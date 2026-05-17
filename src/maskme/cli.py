"""
maskme.cli
~~~~~~~~~~
Command-line entry point.

Usage:
    maskme mask --rules rules.json --input data.csv --output out.csv
    maskme analyze risk --input data.csv --qi age zip --sa diagnosis [--report report.html]
    maskme analyze utility --original orig.csv --anonymized anon.csv [--report report.html]

Legacy flat syntax (still works):
    maskme --rules rules.json --input data.csv --output out.csv

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
from typing import Any, Dict, Generator, List, Optional, Tuple

from maskme.core.engine import MaskMe
from maskme.io import IO_HANDLERS, get_handler
from maskme.strategies import STRATEGIES

from maskme.analytics.risk import METRICS as RISK_METRICS
from maskme.analytics.risk import run as run_risk
from maskme.analytics.risk import report as risk_report
from maskme.analytics.utility import METRICS as UTILITY_METRICS
from maskme.analytics.utility import run as run_utility
from maskme.analytics.utility import report as utility_report

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

def detect_format(input_path: Optional[str], output_path: Optional[str] = None) -> str:
    for path in [input_path, output_path]:
        if path:
            ext = Path(path).suffix.lower().lstrip(".")
            if ext in SUPPORTED_FORMATS:
                return ext
    return DEFAULT_FORMAT


def load_rules(rules_path: str) -> Dict[str, Any]:
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse rules JSON: {e}")


def validate_rules(rules: Dict[str, Any], strategies: Dict[str, Any]) -> None:
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
    count = 0
    for item in it:
        count += 1
        if count % interval == 0:
            logger.info("Processed %d records...", count)
        yield item
    logger.info("Successfully processed %d records.", count)


def load_records(file_path: str, data_format: str) -> List[Dict[str, Any]]:
    """Load all records from a file into a list."""
    handler = get_handler(data_format)
    with get_streams(file_path, None) as (stream, _):
        return list(handler.read(stream))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MaskMe: A modular tool for data anonymization and analytics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # -- mask subcommand ---------------------------------------------------
    mask_p = sub.add_parser(
        "mask",
        help="Anonymize data using masking rules.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    mask_p.add_argument("--rules", required=True,
                        help="Path to the JSON file containing masking rules.")
    mask_p.add_argument("--salt",
                        help="Global salt (overrides MASKME_SALT env var).")
    mask_p.add_argument("--input",
                        help="Path to the source file (stdin if omitted).")
    mask_p.add_argument("--output",
                        help="Path to the destination file (stdout if omitted).")
    mask_p.add_argument("--format", choices=SUPPORTED_FORMATS,
                        help="Data format (inferred from extension if omitted).")
    mask_p.add_argument("--limit", type=int,
                        help="Limit records to process (dry-run).")
    mask_p.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging.")

    # -- ner subcommand ----------------------------------------------------
    ner_p = sub.add_parser(
        "ner",
        help="Anonymize unstructured text using NER (spaCy).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ner_p.add_argument("input", nargs="?",
                       help="Path to a text file (stdin if omitted).")
    ner_p.add_argument("--output", "-o",
                       help="Path to the output file (stdout if omitted).")
    ner_p.add_argument("--language", "-l", default=None,
                       help="Language override ('fr' or 'en'). Auto-detected if omitted.")
    ner_p.add_argument("--lines", action="store_true",
                       help="Treat each line as a separate text (batch mode).")
    ner_p.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging.")

    # -- analyze subcommand ------------------------------------------------
    analyze_p = sub.add_parser(
        "analyze",
        help="Run re-identification risk or data utility analytics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    analyze_sub = analyze_p.add_subparsers(dest="analyze_command")

    # analyze risk
    risk_p = analyze_sub.add_parser(
        "risk",
        help="Re-identification risk metrics (k-anonymity, l-diversity, t-closeness).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    risk_p.add_argument("--input", required=True,
                        help="Path to the anonymised dataset.")
    risk_p.add_argument("--qi", "--quasi-identifiers",
                        nargs="+", required=True, dest="qi",
                        help="Quasi-identifier field names (space-separated).")
    risk_p.add_argument("--sa", "--sensitive-attr",
                        required=True, dest="sa",
                        help="Sensitive attribute field name.")
    risk_p.add_argument("--metrics", nargs="+",
                        choices=list(RISK_METRICS.keys()),
                        default=list(RISK_METRICS.keys()),
                        help="Risk metrics to compute.")
    risk_p.add_argument("--k-threshold", type=int, default=2,
                        help="Minimum equivalence class size for k-anonymity.")
    risk_p.add_argument("--l-threshold", type=int, default=2,
                        help="Minimum distinct sensitive values for l-diversity.")
    risk_p.add_argument("--t-threshold", type=float, default=0.2,
                        help="Maximum EMD per class for t-closeness.")
    risk_p.add_argument("--report",
                        help="Path to write the HTML risk report.")
    risk_p.add_argument("--format", choices=SUPPORTED_FORMATS,
                        help="Data format (inferred from extension if omitted).")
    risk_p.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging.")

    # analyze utility
    util_p = analyze_sub.add_parser(
        "utility",
        help="Data utility metrics (field retention, statistical fidelity, information loss).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    util_p.add_argument("--original", required=True,
                        help="Path to the original (pre-mask) dataset.")
    util_p.add_argument("--anonymized", required=True,
                        help="Path to the anonymised dataset.")
    util_p.add_argument("--numerical-fields", nargs="+",
                        help="Numerical field names (auto-detected if omitted).")
    util_p.add_argument("--categorical-fields", nargs="+",
                        help="Categorical field names (auto-detected if omitted).")
    util_p.add_argument("--metrics", nargs="+",
                        choices=list(UTILITY_METRICS.keys()),
                        default=list(UTILITY_METRICS.keys()),
                        help="Utility metrics to compute.")
    util_p.add_argument("--report",
                        help="Path to write the HTML utility report.")
    util_p.add_argument("--format", choices=SUPPORTED_FORMATS,
                        help="Data format (inferred from extension if omitted).")
    util_p.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging.")

    return parser


# ---------------------------------------------------------------------------
# NER pipeline
# ---------------------------------------------------------------------------

def run_ner(args: argparse.Namespace) -> None:
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    from maskme.ner import mask as ner_mask

    # 1. Read input
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            if args.lines:
                texts = [line.rstrip("\n") for line in f]
            else:
                texts = f.read()
    else:
        if args.lines:
            texts = [line.rstrip("\n") for line in sys.stdin]
        else:
            texts = sys.stdin.read()

    # 2. Process
    if args.lines:
        results = ner_mask(texts, language=args.language)
        outputs = [r.output for r in results]
        n = len(outputs)
        entity_total = sum(r.entity_count for r in results)
    else:
        result = ner_mask(texts, language=args.language)
        outputs = result.output
        n = 1
        entity_total = result.entity_count

    # 3. Write output
    output_text = "\n".join(outputs) if args.lines else outputs
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
            if args.lines:
                f.write("\n")
    else:
        sys.stdout.write(output_text)
        if args.lines:
            sys.stdout.write("\n")

    logger.info("Processed %d text(s), %d entity(ies) detected.", n, entity_total)


# ---------------------------------------------------------------------------
# Masking pipeline
# ---------------------------------------------------------------------------

def run_mask(args: argparse.Namespace) -> None:
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    data_format = args.format or detect_format(args.input, args.output)
    if not args.format and not args.input and not args.output:
        logger.warning(
            "No format specified and no file path to infer from. "
            "Defaulting to '%s'. Use --format to be explicit.",
            DEFAULT_FORMAT,
        )

    rules = load_rules(args.rules)
    validate_rules(rules, STRATEGIES)

    salt = args.salt or os.getenv("MASKME_SALT", "")
    handler = get_handler(data_format)
    engine = MaskMe(rules, salt=salt)

    with get_streams(args.input, args.output) as (input_stream, output_stream):
        records = handler.read(input_stream)
        if args.limit is not None:
            records = islice(records, args.limit)
        masked = engine.mask(records)
        handler.write(tracking_iterator(masked), output_stream)


# ---------------------------------------------------------------------------
# Analytics pipelines
# ---------------------------------------------------------------------------

def _print_risk_results(results: List) -> None:
    n_pass = sum(1 for r in results if r.passed)
    n_total = len(results)
    sep = "═" * 50
    print(f"\n{sep}", file=sys.stderr)
    print("  Re-identification Risk Report", file=sys.stderr)
    print(f"{sep}", file=sys.stderr)
    for r in results:
        icon = "✓" if r.passed else "✗"
        status = "passed" if r.passed else "FAILED"
        print(f"  {icon}  {r.name:<20}", end="", file=sys.stderr)
        extra = r.summary
        if hasattr(r, "name") and "k-Anonymity" in r.name:
            print(f"  k_min={extra.get('k_min')}  "
                  f"{status}  ({extra.get('at_risk_records', 0)} record(s) at risk)",
                  file=sys.stderr)
        elif "l-Diversity" in r.name:
            print(f"  l_min={extra.get('l_min')}  "
                  f"{status}  ({extra.get('at_risk_classes', 0)} class(es) at risk)",
                  file=sys.stderr)
        elif "t-Closeness" in r.name:
            print(f"  t_max={extra.get('t_max')}  "
                  f"{status}  ({extra.get('at_risk_classes', 0)} class(es) at risk)",
                  file=sys.stderr)
        else:
            print(f"  {status}", file=sys.stderr)
    print(f"{sep}", file=sys.stderr)
    print(f"  Summary: {n_pass} of {n_total} metrics PASSED\n", file=sys.stderr)


def _print_utility_results(results: List) -> None:
    n_pass = sum(1 for r in results if r.passed)
    n_total = len(results)
    sep = "═" * 50
    print(f"\n{sep}", file=sys.stderr)
    print("  Data Utility Report", file=sys.stderr)
    print(f"{sep}", file=sys.stderr)
    for r in results:
        icon = "✓" if r.passed else "✗"
        status = "passed" if r.passed else "FAILED"
        print(f"  {icon}  {r.name:<25}  score={r.score:.2f}  {status}", file=sys.stderr)
    print(f"{sep}", file=sys.stderr)
    print(f"  Summary: {n_pass} of {n_total} metrics PASSED\n", file=sys.stderr)


def run_analyze_risk(args: argparse.Namespace) -> None:
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    data_format = args.format or detect_format(args.input)
    records = load_records(args.input, data_format)

    results = run_risk(
        records=records,
        quasi_identifiers=args.qi,
        sensitive_attr=args.sa,
        analytics=args.metrics,
        k_threshold=args.k_threshold,
        l_threshold=args.l_threshold,
        t_threshold=args.t_threshold,
    )

    _print_risk_results(results)

    if args.report:
        risk_report.generate(results, args.report)
        logger.info("Risk report written to: %s", args.report)


def run_analyze_utility(args: argparse.Namespace) -> None:
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    data_format = args.format or detect_format(args.original)
    original = load_records(args.original, data_format)
    anonymised = load_records(args.anonymized, data_format)

    results = run_utility(
        original=original,
        anonymised=anonymised,
        numerical_fields=args.numerical_fields,
        categorical_fields=args.categorical_fields,
        metrics=args.metrics,
    )

    _print_utility_results(results)

    if args.report:
        utility_report.generate(results, args.report)
        logger.info("Utility report written to: %s", args.report)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_COMMANDS = {
    "ner": run_ner,
    "mask": run_mask,
    ("analyze", "risk"): run_analyze_risk,
    ("analyze", "utility"): run_analyze_utility,
}


def main() -> None:
    """
    Parse arguments and dispatch to the appropriate subcommand.

    Exit codes:
        0 — success
        1 — known error (missing file, invalid input)
        2 — unexpected error (bug)
    """
    parser = build_parser()

    try:
        # Backward compat: if the first argument is a flag (starts with '-'),
        # inject 'mask' so `maskme --rules ...` still works.
        if len(sys.argv) <= 1 or sys.argv[1] in ("-h", "--help"):
            parser.print_help()
            sys.exit(0)
        elif not sys.argv[1].startswith("-"):
            args = parser.parse_args()
        else:
            args = parser.parse_args(["mask"] + sys.argv[1:])

        if args.command == "analyze":
            key = (args.command, args.analyze_command)
        else:
            key = args.command

        handler = _COMMANDS.get(key)
        if handler is None:
            parser.print_help()
            sys.exit(1)

        handler(args)

    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error — please report this as a bug.")
        sys.exit(2)


if __name__ == "__main__":
    main()
