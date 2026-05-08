"""
maskme.io.json_handler
~~~~~~~~~~~~~~~~~~~~~~~
Standard JSON format handler.

Memory note:
    JSON is not a streaming-friendly format. read() must load the entire
    file into memory before yielding any records. For large datasets,
    prefer JSONL format (jsonl_handler) which supports true line-by-line
    streaming.

    write() streams records one at a time by building the JSON array
    manually, avoiding the full in-memory materialisation of list(records).
"""

import json
import logging
from typing import Any, Dict, Iterable

logger = logging.getLogger(__name__)


class JSONHandler:
    """
    Handles standard JSON files (a list of objects, or a single object).

    Read:  Loads the full file into memory (JSON format limitation).
    Write: Streams records into a JSON array without full materialisation.
    """

    def read(self, stream: Any) -> Iterable[Dict]:
        """
        Load a JSON file and yield each record as a dict.

        Supports two shapes:
          - A JSON array  → each element is yielded as a record.
          - A JSON object → yielded as a single record.

        Warning:
            The entire file is loaded into memory before the first record
            is yielded. For large files, use JSONL format instead.

        Args:
            stream: A readable file-like object (text mode).

        Yields:
            One dict per record.
        """
        data = json.load(stream)
        if isinstance(data, list):
            yield from data
        else:
            yield data

    def write(self, records: Iterable[Dict], stream: Any) -> None:
        """
        Write records as a JSON array, streaming one record at a time.

        Builds the JSON array incrementally to avoid loading all records
        into memory at once. The output is a well-formed JSON array.

        Args:
            records: An iterable of dicts to write.
            stream:  A writable file-like object (text mode).
        """
        stream.write("[\n")
        first = True

        for record in records:
            if not first:
                stream.write(",\n")
            stream.write("    " + json.dumps(record, ensure_ascii=False))
            first = False

        stream.write("\n]")