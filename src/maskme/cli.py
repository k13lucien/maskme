import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Internal imports
from maskme.core.core import MaskMe
from maskme.io import get_handler

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
    
    # Input/Output
    parser.add_argument(
        "--input", 
        help="Path to the source file (reads from stdin if not provided)."
    )
    parser.add_argument(
        "--output", 
        help="Path to the destination file (writes to stdout if not provided)."
    )
    
    # Format selection
    parser.add_argument(
        "--format", 
        choices=["csv", "json", "jsonl"], 
        default="csv", 
        help="Data format of the input/output."
    )

    args = parser.parse_args()

    # 1. Initialize the I/O Handler via the registry
    try:
        handler = get_handler(args.format)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load Masking Rules
    rules = load_rules(args.rules)

    # 3. Setup Streams (Files or Standard I/O)
    # Using newline='' for CSV compliance on Windows/Unix
    input_stream = open(args.input, 'r', encoding='utf-8') if args.input else sys.stdin
    output_stream = open(args.output, 'w', encoding='utf-8', newline='') if args.output else sys.stdout

    try:
        # 4. Initialize Core Engine
        engine = MaskMe(rules)
        
        # 5. Execute the Pipeline (Streaming Approach)
        # Handler.read yields dicts -> engine.mask transforms -> handler.write persists
        records_iterator = handler.read(input_stream)
        masked_iterator = engine.mask(records_iterator)
        
        handler.write(masked_iterator, output_stream)
        
        # Optional: Print success message to stderr (to not pollute stdout)
        if args.input:
            print(f"Successfully processed {args.input} using {args.format} format.", file=sys.stderr)

    except Exception as e:
        print(f"Unexpected Runtime Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # 6. Clean up resources
        if args.input:
            input_stream.close()
        if args.output:
            output_stream.close()

if __name__ == "__main__":
    main()