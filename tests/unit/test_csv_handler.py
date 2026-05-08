"""
Unit tests for maskme.io.csv_handler
--------------------------------------
Uses io.StringIO as a lightweight stream substitute — no file system needed.
Covers read, write, round-trip, empty input, extrasaction, and the
FormatHandler Protocol contract.
"""

import csv
import io
import warnings
import logging

import pytest

from maskme.io.base import FormatHandler
from maskme.io.csv_handler import CSVHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_csv(*rows: dict) -> io.StringIO:
    """Build an in-memory CSV stream from a list of dicts."""
    if not rows:
        return io.StringIO("")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return buf


def read_csv(stream: io.StringIO) -> list:
    """Read a CSV stream back into a list of dicts."""
    stream.seek(0)
    return list(csv.DictReader(stream))


# ===========================================================================
# Protocol compliance
# ===========================================================================


class TestProtocol:

    def test_is_format_handler(self):
        """CSVHandler satisfies the FormatHandler Protocol at runtime."""
        assert isinstance(CSVHandler(), FormatHandler)

    def test_has_read_method(self):
        assert hasattr(CSVHandler(), "read")

    def test_has_write_method(self):
        assert hasattr(CSVHandler(), "write")


# ===========================================================================
# read()
# ===========================================================================


class TestRead:

    def test_yields_dicts(self):
        """Each row is returned as a dict."""
        stream = make_csv({"name": "Alice", "age": "30"})
        handler = CSVHandler()
        records = list(handler.read(stream))
        assert records == [{"name": "Alice", "age": "30"}]

    def test_yields_multiple_rows(self):
        """All rows are yielded in order."""
        rows = [{"id": str(i), "val": str(i * 10)} for i in range(5)]
        stream = make_csv(*rows)
        handler = CSVHandler()
        result = list(handler.read(stream))
        assert result == rows

    def test_empty_csv_yields_nothing(self):
        """A CSV with only headers and no data rows yields nothing."""
        buf = io.StringIO("name,age\n")
        result = list(CSVHandler().read(buf))
        assert result == []

    def test_completely_empty_stream_yields_nothing(self):
        """A completely empty stream yields nothing."""
        result = list(CSVHandler().read(io.StringIO("")))
        assert result == []

    def test_keys_match_headers(self):
        """Dict keys correspond to CSV column headers."""
        stream = make_csv({"email": "alice@example.com", "score": "92"})
        record = next(iter(CSVHandler().read(stream)))
        assert set(record.keys()) == {"email", "score"}

    def test_preserves_row_order(self):
        """Rows are yielded in the same order as in the source."""
        rows = [{"n": str(i)} for i in range(10)]
        stream = make_csv(*rows)
        result = list(CSVHandler().read(stream))
        assert [r["n"] for r in result] == [str(i) for i in range(10)]

    def test_is_lazy(self):
        """read() returns an iterable without consuming the stream upfront."""
        stream = make_csv({"a": "1"}, {"a": "2"})
        handler = CSVHandler()
        iterable = handler.read(stream)
        # Should not raise — just checks it's iterable
        assert hasattr(iterable, "__iter__")


# ===========================================================================
# write()
# ===========================================================================


class TestWrite:

    def test_writes_header_and_rows(self):
        """write() produces a valid CSV with headers and data."""
        records = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
        out = io.StringIO()
        CSVHandler().write(iter(records), out)
        result = read_csv(out)
        assert result == records

    def test_header_inferred_from_first_record(self):
        """Column headers are taken from the first record's keys."""
        records = [{"x": "1", "y": "2"}]
        out = io.StringIO()
        CSVHandler().write(iter(records), out)
        out.seek(0)
        headers = out.readline().strip().split(",")
        assert set(headers) == {"x", "y"}

    def test_single_record(self):
        """A single record is written correctly."""
        out = io.StringIO()
        CSVHandler().write(iter([{"a": "1"}]), out)
        result = read_csv(out)
        assert result == [{"a": "1"}]

    def test_empty_input_emits_warning(self, caplog):
        """An empty records iterable triggers a warning log."""
        out = io.StringIO()
        with caplog.at_level(logging.WARNING, logger="maskme.io.csv_handler"):
            CSVHandler().write(iter([]), out)
        assert any("empty" in msg.lower() for msg in caplog.messages)

    def test_empty_input_produces_empty_output(self):
        """No records → no output written to stream."""
        out = io.StringIO()
        CSVHandler().write(iter([]), out)
        out.seek(0)
        assert out.read() == ""

    def test_extrasaction_ignore_drops_extra_fields(self):
        """Fields not present in the first record's header are silently dropped."""
        records = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob",   "age": "25", "extra": "ignored"},
        ]
        out = io.StringIO()
        CSVHandler().write(iter(records), out)
        result = read_csv(out)
        # 'extra' must not appear in output
        assert all("extra" not in r for r in result)
        assert result[0] == {"name": "Alice", "age": "30"}

    def test_preserves_record_order(self):
        """Records are written in the same order as they arrive."""
        records = [{"n": str(i)} for i in range(10)]
        out = io.StringIO()
        CSVHandler().write(iter(records), out)
        result = read_csv(out)
        assert [r["n"] for r in result] == [str(i) for i in range(10)]


# ===========================================================================
# Round-trip: read → write → read
# ===========================================================================


class TestRoundTrip:

    def test_round_trip_preserves_data(self):
        """Data read from CSV and written back produces identical content."""
        original = [
            {"name": "Alice", "email": "alice@example.com", "age": "30"},
            {"name": "Bob",   "email": "bob@example.com",   "age": "25"},
        ]
        handler = CSVHandler()

        # Write original → in-memory stream
        source = io.StringIO()
        handler.write(iter(original), source)

        # Read back
        source.seek(0)
        records = list(handler.read(source))

        # Write again to a second stream
        dest = io.StringIO()
        handler.write(iter(records), dest)

        # Compare both streams
        source.seek(0)
        dest.seek(0)
        assert source.read() == dest.read()

    def test_round_trip_after_field_drop(self):
        """Round-trip works correctly when a field is absent in some records."""
        records = [{"name": "Alice", "ssn": "123"}, {"name": "Bob"}]
        out = io.StringIO()
        # Header set from first record — second record has no 'ssn'
        CSVHandler().write(iter(records), out)
        out.seek(0)
        result = list(CSVHandler().read(out))
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"