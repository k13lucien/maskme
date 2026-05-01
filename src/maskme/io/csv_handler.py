import csv
from typing import Iterable, Dict

class CSVHandler:
    """Handles CSV reading and writing using streaming to save memory."""
    
    def read(self, stream) -> Iterable[Dict]:
        """Yields each row as a dictionary."""
        return csv.DictReader(stream)

    def write(self, records: Iterable[Dict], stream):
        """Writes records to the stream, initializing headers from the first record."""
        writer = None
        for record in records:
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=record.keys())
                writer.writeheader()
            writer.writerow(record)