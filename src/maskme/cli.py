import argparse
import json
import logging
import os
import sys
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

# Internal imports
from maskme.core.core import MaskMe
from maskme.io import get_handler
from maskme.strategies import STRATEGIES

# Constants
DEFAULT_FORMAT = 'csv'
PROGRESS_INTERVAL = 1000
SUPPORTED_FORMATS = ['csv', 'json', 'jsonl']

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def detect_format(input_path: Optional[str], output_path: Optional[str]) -> str:
    """
    Infers the data format from file extensions.
    Priority: Input extension > Output extension > Default (csv).
    """
    for path in [input_path, output_path]:
        if path:
            ext = Path(path).suffix.lower().lstrip('.')
            if ext in SUPPORTED_FORMATS:
                return ext
    return DEFAULT_FORMAT

def validate_rules(rules: Dict[str, Any]) -> None:
    """
    Verifies that all strategies defined in the rules exist in the registry.
    """
    invalid_strategies = []
    for path, config in rules.items():
        strategy_name = config.get("strategy") if isinstance(config, dict) else config
        if strategy_name not in STRATEGIES:
            invalid_strategies.append(f"{path}: {strategy_name}")
    
    if invalid_strategies:
        logger.error("Invalid strategies found in rules:\n  - %s", "\n  - ".join(invalid_strategies))
        sys.exit(1)

def load_rules(rules_path: str) -> Dict[str, Any]:
    """
    Safely loads the JSON configuration file for masking rules.
    """
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Rules file not found at %s", rules_path)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse rules JSON: %s", e)
        sys.exit(1)

@contextmanager
def get_streams(input_path: Optional[str], output_path: Optional[str]) -> Generator[Tuple[Any, Any], None, None]:
    """
    Context manager to safely handle input and output streams.
    """
    input_stream = open(input_path, 'r', encoding='utf-8') if input_path else sys.stdin
    output_stream = open(output_path, 'w', encoding='utf-8', newline='') if output_path else sys.stdout
    
    try:
        yield input_stream, output_stream
    finally:
        if input_path:
            input_stream.close()
        if output_path:
            output_stream.close()

def tracking_iterator(it: Generator, interval: int = PROGRESS_INTERVAL) -> Generator:
    """
    Yields items from an iterator and logs progress at regular intervals.
    """
    count = 0
    for item in it:
        count += 1
        if count % interval == 0:
            logger.info("Processed %d records...", count)
        yield item
    
    logger.info("Successfully processed %d records.", count)

def parse_args() -> argparse.Namespace:
    """
    Defines and parses CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="MaskMe CLI: A modular tool for data anonymization and privacy.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Configuration
    parser.add_argument("--rules", required=True, help="Path to the JSON file containing masking rules.")
    parser.add_argument("--salt", help="Global salt for cryptographic operations (overrides MASKME_SALT env var).")
    
    # Input/Output
    parser.add_argument("--input", help="Path to the source file (reads from stdin if not provided).")
    parser.add_argument("--output", help="Path to the destination file (writes to stdout if not provided).")
    
    # Processing options
    parser.add_argument("--format", choices=SUPPORTED_FORMATS, help="Data format. Inferred from file extensions if not provided.")
    parser.add_argument("--limit", type=int, help="Limit the number of records to process (useful for dry-runs).")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    return parser.parse_args()

def run_pipeline(args: argparse.Namespace) -> None:
    """
    Orchestrates the data masking pipeline.
    """
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 1. Configuration & Setup
    data_format = args.format or detect_format(args.input, args.output)
    rules = load_rules(args.rules)
    validate_rules(rules)
    
    salt = args.salt or os.getenv("MASKME_SALT", "")
    handler = get_handler(data_format)
    engine = MaskMe(rules, salt=salt)

    # 2. Processing
    with get_streams(args.input, args.output) as (input_stream, output_stream):
        records = handler.read(input_stream)
        
        if args.limit is not None:
            records = islice(records, args.limit)
            
        masked_records = engine.mask(records)
        handler.write(tracking_iterator(masked_records), output_stream)

def main():
    try:
        args = parse_args()
        run_pipeline(args)
    except Exception as e:
        logger.error("Unexpected Runtime Error: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
