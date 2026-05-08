"""
maskme.cli
~~~~~~~~~~
Command-line entry point for the MaskMe anonymization pipeline.

Usage examples:
    # File to file (format inferred from extension)
    maskme --rules rules.json --input data.csv --output out.csv

    # Stdin to stdout with explicit format
    cat data.jsonl | maskme --rules rules.json --format jsonl > out.jsonl

    # Dry-run on first 100 records
    maskme --rules rules.json --input data.csv --limit 100

Environment variables:
    MASKME_SALT   Global salt for cryptographic operations (overridden by --salt).
"""

import argparse
import json
import logging
import os
import sys
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

from maskme.core.engine import MaskMe
from maskme.io import IO_HANDLERS, get_handler
from maskme.strategies import STRATEGIES

# Derived from the single source of truth — never duplicate this list.
SUPPORTED_FORMATS = list(IO_HANDLERS.keys())
DEFAULT_FORMAT = "csv"
PROGRESS_INTERVAL = 1000

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def detect_format(input_path: Optional[str], output_path: Optional[str]) -> str:
    """
    Infer the data format from file extensions.

    Priority: input extension → output extension → DEFAULT_FORMAT.

    Args:
        input_path:  Path to the input file, or None for stdin.
        output_path: Path to the output file, or None for stdout.

    Returns:
        The inferred format string (e.g. "csv", "jsonl").
    """
    for path in [input_path, output_path]:
        if path:
            ext = Path(path).suffix.lower().lstrip(".")
            if ext in SUPPORTED_FORMATS:
                return ext
    return DEFAULT_FORMAT


def load_rules(rules_path: str) -> Dict[str, Any]:
    """
    Load and parse a JSON rules file.

    Args:
        rules_path: Path to the JSON file containing masking rules.

    Returns:
        Parsed rules as a dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If the file contains invalid JSON.
    """
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse rules JSON: {e}")


def validate_rules(rules: Dict[str, Any], strategies: Dict[str, Any]) -> None:
    """
    Verify that all strategy names in the rules exist in the registry.

    Receiving strategies as a parameter makes this function testable
    without coupling it to the global STRATEGIES import.

    Args:
        rules:      The masking rules dict (path → strategy config).
        strategies: The strategy registry to validate against.

    Raises:
        ValueError: If one or more strategy names are not registered.
    """
    invalid = []
    for path, config in rules.items():
        name = config.get("strategy") if isinstance(config, dict) else config
        if name not in strategies:
            invalid.append(f"  {path}: '{name}'")

    if invalid:
        raise ValueError(
            "Invalid strategies found in rules:\n" + "\n".join(invalid)
        )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

@contextmanager
def get_streams(
    input_path: Optional[str],
    output_path: Optional[str],
) -> Generator[Tuple[Any, Any], None, None]:
    """
    Context manager that opens input and output streams safely.

    Falls back to sys.stdin / sys.stdout when paths are not provided.

    Args:
        input_path:  Path to the input file, or None for stdin.
        output_path: Path to the output file, or None for stdout.

    Yields:
        (input_stream, output_stream) tuple.
    """
    input_stream = (
        open(input_path, "r", encoding="utf-8") if input_path else sys.stdin
    )
    output_stream = (
        open(output_path, "w", encoding="utf-8", newline="")
        if output_path
        else sys.stdout
    )
    try:
        yield input_stream, output_stream
    finally:
        if input_path:
            input_stream.close()
        if output_path:
            output_stream.close()


def tracking_iterator(
    it: Generator, interval: int = PROGRESS_INTERVAL
) -> Generator:
    """
    Wrap an iterator to log progress at regular intervals.

    Args:
        it:       The source iterator to wrap.
        interval: Number of records between each progress log.

    Yields:
        Items from the source iterator, unchanged.
    """
    count = 0
    for item in it:
        count += 1
        if count % interval == 0:
            logger.info("Processed %d records...", count)
        yield item
    logger.info("Successfully processed %d records.", count)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="MaskMe CLI: A modular tool for data anonymization.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--rules", required=True,
        help="Path to the JSON file containing masking rules.",
    )
    parser.add_argument(
        "--salt",
        help="Global salt for cryptographic operations (overrides MASKME_SALT env var).",
    )
    parser.add_argument(
        "--input",
        help="Path to the source file (reads from stdin if not provided).",
    )
    parser.add_argument(
        "--output",
        help="Path to the destination file (writes to stdout if not provided).",
    )
    parser.add_argument(
        "--format", choices=SUPPORTED_FORMATS,
        help="Data format. Inferred from file extensions if not provided.",
    )
    parser.add_argument(
        "--limit", type=int,
        help="Limit the number of records to process (useful for dry-runs).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(args: argparse.Namespace) -> None:
    """
    Orchestrate the full data anonymization pipeline.

    Steps:
        1. Resolve configuration (format, salt, rules).
        2. Validate rules against the strategy registry.
        3. Stream records through the engine and write output.

    Args:
        args: Parsed CLI arguments.

    Raises:
        FileNotFoundError: If the rules file is missing.
        ValueError:        If rules contain unknown strategies.
    """
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 1. Format detection
    data_format = args.format or detect_format(args.input, args.output)
    if not args.format and not args.input and not args.output:
        logger.warning(
            "No format specified and no file path to infer from. "
            "Defaulting to '%s'. Use --format to be explicit.",
            DEFAULT_FORMAT,
        )

    # 2. Rules loading and validation
    rules = load_rules(args.rules)
    validate_rules(rules, STRATEGIES)

    # 3. Engine and handler setup
    salt = args.salt or os.getenv("MASKME_SALT", "")
    handler = get_handler(data_format)
    engine = MaskMe(rules, salt=salt)

    # 4. Streaming pipeline
    with get_streams(args.input, args.output) as (input_stream, output_stream):
        records = handler.read(input_stream)

        if args.limit is not None:
            records = islice(records, args.limit)

        masked = engine.mask(records)
        handler.write(tracking_iterator(masked), output_stream)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Parse arguments and run the pipeline.

    Exit codes:
        0 — success
        1 — known error (missing file, invalid rules, bad format)
        2 — unexpected error (bug)
    """
    try:
        args = parse_args()
        run_pipeline(args)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error — please report this as a bug.")
        sys.exit(2)


if __name__ == "__main__":
    main()