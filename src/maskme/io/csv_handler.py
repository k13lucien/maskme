"""
maskme.io.csv_handler
~~~~~~~~~~~~~~~~~~~~~
CSV format handler — streaming read, lazy write.
"""

import csv
import logging
from typing import Any, Dict, Iterable

logger = logging.getLogger(__name__)


class CSVHandler:
    """
    Handles CSV reading and writing using streaming to preserve memory.

    Read:  Yields one dict per row via csv.DictReader — no full load.
    Write: Writes records one at a time. Headers are inferred from the
           first record. Emits a warning if the input is empty.
    """

    def read(self, stream: Any) -> Iterable[Dict]:
        """
        Yield each CSV row as a dict.

        Args:
            stream: A readable file-like object (text mode).

        Yields:
            One dict per row, keyed by column headers.
        """
        return csv.DictReader(stream)

    def write(self, records: Iterable[Dict], stream: Any) -> None:
        """
        Write records to a CSV stream, inferring headers from the first record.

        Uses extrasaction='ignore' so that fields absent from the header
        (e.g. added by a strategy mid-pipeline) are silently dropped rather
        than raising a ValueError.

        Emits a warning if the records iterable is empty, since the output
        file will contain no data (not even headers).

        Args:
            records: An iterable of dicts to write.
            stream:  A writable file-like object (text mode).
        """
        writer = None

        for record in records:
            if writer is None:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=record.keys(),
                    extrasaction="ignore",
                )
                writer.writeheader()
            writer.writerow(record)

        if writer is None:
            logger.warning(
                "CSVHandler.write: no records received — output will be empty."
            )