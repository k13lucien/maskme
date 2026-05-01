import json
from typing import Iterable, Dict

class JSONLHandler:
    """Handles JSON Lines format (one JSON object per line)."""

    def read(self, stream) -> Iterable[Dict]:
        """Yields dictionaries line by line."""
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)

    def write(self, records: Iterable[Dict], stream):
        """Writes dictionaries as JSON strings, one per line."""
        for record in records:
            stream.write(json.dumps(record) + "\n")