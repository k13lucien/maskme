import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Internal imports
from maskme.core.core import MaskMe
from maskme.io import get_handler
from maskme.strategies import STRATEGIES

def detect_format(input_path: Optional[str], output_path: Optional[str]) -> str:
    """
    Infers the data format from file extensions.
    Priority: Input extension > Output extension > Default (csv).
    """
    for path in [input_path, output_path]:
        if path:
            ext = Path(path).suffix.lower().lstrip('.')
            if ext in ['csv', 'json', 'jsonl']:
                return ext
    return 'csv'

def validate_rules(rules: Dict[str, Any]):
    """
    Verifies that all strategies defined in the rules exist in the registry.
    """
    invalid_strategies = []
    for path, config in rules.items():
        strategy_name = config.get("strategy") if isinstance(config, dict) else config
        if strategy_name not in STRATEGIES:
            invalid_strategies.append(f"{path}: {strategy_name}")
    
    if invalid_strategies:
        print("Error: Invalid strategies found in rules:", file=sys.stderr)
        for error in invalid_strategies:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

def load_rules(rules_path: str) -> Dict[str, Any]:
    """
    Safely loads the JSON configuration file for masking rules.
    """
    path = Path(rules_path)
    if not path.exists():
        print(f"Error: Rules file not found at {rules_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse rules JSON: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Main entry point for the MaskMe CLI.
    Orchestrates the flow: Input Stream -> Handler -> Core Engine -> Output Stream.
    """
    parser = argparse.ArgumentParser(
        description="MaskMe CLI: A modular tool for data anonymization and privacy.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Configuration
    parser.add_argument(
        "--rules", 
        required=True, 
        help="Path to the JSON file containing masking rules."
    )
    parser.add_argument(
        "--salt", 
        help="Global salt for cryptographic operations (overrides MASKME_SALT env var)."
    )
    
    # Input/Output
    parser.add_argument(
        "--input", 
        help="Path to the source file (reads from stdin if not provided)."
    )
    parser.add_argument(
        "--output", 
        help="Path to the destination file (writes to stdout if not provided)."
    )
    
    # Processing options
    parser.add_argument(
        "--format", 
        choices=["csv", "json", "jsonl"], 
        help="Data format. Inferred from file extensions if not provided."
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        help="Limit the number of records to process (useful for dry-runs)."
    )

    args = parser.parse_args()

    # 1. Resolve Data Format
    data_format = args.format or detect_format(args.input, args.output)

    # 2. Initialize the I/O Handler
    try:
        handler = get_handler(data_format)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Load and Validate Masking Rules
    rules = load_rules(args.rules)
    validate_rules(rules)

    # 4. Resolve Salt
    salt = args.salt or os.getenv("MASKME_SALT", "")

    # 5. Setup Streams
    input_stream = open(args.input, 'r', encoding='utf-8') if args.input else sys.stdin
    output_stream = open(args.output, 'w', encoding='utf-8', newline='') if args.output else sys.stdout

    try:
        # 6. Initialize Core Engine
        engine = MaskMe(rules, salt=salt)
        
        # 7. Execute the Pipeline (Streaming Approach)
        records_iterator = handler.read(input_stream)
        
        # Apply limit if requested
        if args.limit is not None:
            from itertools import islice
            records_iterator = islice(records_iterator, args.limit)

        masked_iterator = engine.mask(records_iterator)
        
        # Write results while tracking progress
        count = 0
        def tracking_iterator(it):
            nonlocal count
            for item in it:
                count += 1
                if count % 1000 == 0:
                    print(f"  Processed {count} records...", file=sys.stderr)
                yield item

        handler.write(tracking_iterator(masked_iterator), output_stream)
        
        # Final success message
        source = args.input if args.input else "stdin"
        print(f"Successfully processed {count} records from {source} using {data_format} format.", file=sys.stderr)

    except Exception as e:
        print(f"Unexpected Runtime Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # 8. Clean up resources
        if args.input:
            input_stream.close()
        if args.output:
            output_stream.close()

if __name__ == "__main__":
    main()