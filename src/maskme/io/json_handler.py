import json
from typing import Iterable, Dict

class JSONHandler:
    """Handles standard JSON files (typically a list of objects)."""

    def read(self, stream) -> Iterable[Dict]:
        """Loads the entire JSON list and yields objects."""
        data = json.load(stream)
        if isinstance(data, list):
            for item in data:
                yield item
        else:
            yield data

    def write(self, records: Iterable[Dict], stream):
        """Writes all records as a single JSON list."""
        # Note: This materializes the list in memory to write it properly
        json.dump(list(records), stream, indent=4)