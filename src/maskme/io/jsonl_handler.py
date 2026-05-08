"""
maskme.io.jsonl_handler
~~~~~~~~~~~~~~~~~~~~~~~~
JSON Lines format handler — true line-by-line streaming.

JSONL is the recommended format for large datasets: each line is an
independent JSON object, enabling both read and write to operate in
constant memory regardless of dataset size.
"""

import json
import logging
from typing import Any, Dict, Iterable

logger = logging.getLogger(__name__)


class JSONLHandler:
    """
    Handles JSON Lines format (one JSON object per line).

    Read:  Yields one dict per non-empty line. Malformed lines are
           logged and skipped rather than crashing the pipeline.
    Write: Writes one JSON object per line — true streaming, no
           in-memory accumulation.
    """

    def read(self, stream: Any) -> Iterable[Dict]:
        """
        Yield one dict per non-empty line in the stream.

        Malformed lines are logged with their line number and skipped,
        allowing the pipeline to continue processing valid records.

        Args:
            stream: A readable file-like object (text mode).

        Yields:
            One dict per valid JSON line.
        """
        for line_num, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Skipping malformed JSON on line %d: %s", line_num, e
                )

    def write(self, records: Iterable[Dict], stream: Any) -> None:
        """
        Write one JSON object per line to the stream.

        Each record is serialised independently — constant memory usage
        regardless of dataset size.

        Args:
            records: An iterable of dicts to write.
            stream:  A writable file-like object (text mode).
        """
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")