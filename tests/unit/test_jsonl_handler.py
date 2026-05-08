"""
Unit tests for maskme.io.jsonl_handler
----------------------------------------
Uses io.StringIO as a lightweight stream substitute — no file system needed.
Covers read, write, round-trip, malformed line handling, and FormatHandler
Protocol compliance.
"""

import io
import json
import logging

import pytest

from maskme.io.base import FormatHandler
from maskme.io.jsonl_handler import JSONLHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jsonl_stream(*records: dict) -> io.StringIO:
    """Build an in-memory JSONL stream from a list of dicts."""
    buf = io.StringIO()
    for record in records:
        buf.write(json.dumps(record, ensure_ascii=False) + "\n")
    buf.seek(0)
    return buf


def read_jsonl(stream: io.StringIO) -> list:
    """Parse a JSONL stream back into a list of dicts."""
    stream.seek(0)
    return [json.loads(line) for line in stream if line.strip()]


# ===========================================================================
# Protocol compliance
# ===========================================================================


class TestProtocol:

    def test_is_format_handler(self):
        """JSONLHandler satisfies the FormatHandler Protocol at runtime."""
        assert isinstance(JSONLHandler(), FormatHandler)

    def test_has_read_method(self):
        assert hasattr(JSONLHandler(), "read")

    def test_has_write_method(self):
        assert hasattr(JSONLHandler(), "write")


# ===========================================================================
# read()
# ===========================================================================


class TestRead:

    def test_yields_dicts(self):
        """Each line is returned as a dict."""
        stream = make_jsonl_stream({"name": "Alice"}, {"name": "Bob"})
        result = list(JSONLHandler().read(stream))
        assert result == [{"name": "Alice"}, {"name": "Bob"}]

    def test_yields_single_record(self):
        stream = make_jsonl_stream({"a": 1})
        result = list(JSONLHandler().read(stream))
        assert result == [{"a": 1}]

    def test_empty_stream_yields_nothing(self):
        result = list(JSONLHandler().read(io.StringIO("")))
        assert result == []

    def test_skips_blank_lines(self):
        """Blank lines between records are silently ignored."""
        buf = io.StringIO('{"a": 1}\n\n{"b": 2}\n\n')
        result = list(JSONLHandler().read(buf))
        assert result == [{"a": 1}, {"b": 2}]

    def test_skips_whitespace_only_lines(self):
        """Lines containing only whitespace are skipped."""
        buf = io.StringIO('{"a": 1}\n   \n{"b": 2}\n')
        result = list(JSONLHandler().read(buf))
        assert result == [{"a": 1}, {"b": 2}]

    def test_preserves_record_order(self):
        """Records are yielded in the same order as in the source."""
        records = [{"n": i} for i in range(10)]
        stream = make_jsonl_stream(*records)
        result = list(JSONLHandler().read(stream))
        assert result == records

    def test_preserves_unicode_characters(self):
        """Unicode characters in values are read correctly."""
        stream = make_jsonl_stream({"name": "Ouédraogo"}, {"city": "Ouagadougou"})
        result = list(JSONLHandler().read(stream))
        assert result[0]["name"] == "Ouédraogo"
        assert result[1]["city"] == "Ouagadougou"

    def test_preserves_value_types(self):
        """Integer, float, bool and None values are preserved."""
        record = {"count": 42, "score": 3.14, "active": True, "note": None}
        stream = make_jsonl_stream(record)
        result = list(JSONLHandler().read(stream))
        assert result == [record]

    def test_preserves_nested_values(self):
        """Nested dicts and lists within records are preserved."""
        record = {"user": {"email": "alice@example.com"}, "tags": ["a", "b"]}
        stream = make_jsonl_stream(record)
        result = list(JSONLHandler().read(stream))
        assert result == [record]

    def test_is_lazy(self):
        """read() yields records one at a time without loading all upfront."""
        stream = make_jsonl_stream({"a": 1}, {"b": 2}, {"c": 3})
        gen = JSONLHandler().read(stream)
        first = next(gen)
        assert first == {"a": 1}


# ===========================================================================
# read() — malformed line handling
# ===========================================================================


class TestMalformedLines:

    def test_malformed_line_is_skipped(self, caplog):
        """A malformed line does not crash the pipeline."""
        buf = io.StringIO('{"a": 1}\nnot valid json\n{"b": 2}\n')
        with caplog.at_level(logging.WARNING, logger="maskme.io.jsonl_handler"):
            result = list(JSONLHandler().read(buf))
        assert result == [{"a": 1}, {"b": 2}]

    def test_malformed_line_emits_warning(self, caplog):
        """A malformed line triggers a warning log with the line number."""
        buf = io.StringIO('{"a": 1}\nnot valid json\n{"b": 2}\n')
        with caplog.at_level(logging.WARNING, logger="maskme.io.jsonl_handler"):
            list(JSONLHandler().read(buf))
        assert len(caplog.records) == 1
        assert "2" in caplog.records[0].message  # line number

    def test_multiple_malformed_lines_each_emit_warning(self, caplog):
        """Each malformed line emits its own warning."""
        buf = io.StringIO("bad1\nbad2\n{\"c\": 3}\n")
        with caplog.at_level(logging.WARNING, logger="maskme.io.jsonl_handler"):
            result = list(JSONLHandler().read(buf))
        assert result == [{"c": 3}]
        assert len(caplog.records) == 2

    def test_all_malformed_yields_nothing(self, caplog):
        """If all lines are malformed, nothing is yielded."""
        buf = io.StringIO("bad1\nbad2\nbad3\n")
        with caplog.at_level(logging.WARNING, logger="maskme.io.jsonl_handler"):
            result = list(JSONLHandler().read(buf))
        assert result == []
        assert len(caplog.records) == 3

    def test_valid_records_after_malformed_are_yielded(self):
        """Valid records following a malformed line are not lost."""
        buf = io.StringIO('{"a": 1}\nbad\n{"b": 2}\n{"c": 3}\n')
        result = list(JSONLHandler().read(buf))
        assert {"b": 2} in result
        assert {"c": 3} in result


# ===========================================================================
# write()
# ===========================================================================


class TestWrite:

    def test_writes_one_record_per_line(self):
        """Each record occupies exactly one line."""
        records = [{"a": 1}, {"b": 2}, {"c": 3}]
        out = io.StringIO()
        JSONLHandler().write(iter(records), out)
        out.seek(0)
        lines = [l for l in out.readlines() if l.strip()]
        assert len(lines) == 3

    def test_each_line_is_valid_json(self):
        """Every line in the output is parseable as JSON."""
        records = [{"name": "Alice"}, {"name": "Bob"}]
        out = io.StringIO()
        JSONLHandler().write(iter(records), out)
        out.seek(0)
        for line in out:
            if line.strip():
                parsed = json.loads(line)
                assert isinstance(parsed, dict)

    def test_empty_input_produces_empty_output(self):
        """No records → empty output stream."""
        out = io.StringIO()
        JSONLHandler().write(iter([]), out)
        out.seek(0)
        assert out.read() == ""

    def test_preserves_unicode_characters(self):
        """Unicode characters are written without ASCII escaping."""
        out = io.StringIO()
        JSONLHandler().write(iter([{"name": "Ouédraogo"}]), out)
        out.seek(0)
        assert "Ouédraogo" in out.read()

    def test_preserves_value_types(self):
        """Integer, float, bool and None survive serialisation."""
        record = {"count": 42, "score": 3.14, "active": True, "note": None}
        out = io.StringIO()
        JSONLHandler().write(iter([record]), out)
        result = read_jsonl(out)
        assert result == [record]

    def test_preserves_record_order(self):
        """Records are written in the same order as they arrive."""
        records = [{"n": i} for i in range(10)]
        out = io.StringIO()
        JSONLHandler().write(iter(records), out)
        result = read_jsonl(out)
        assert [r["n"] for r in result] == list(range(10))


# ===========================================================================
# Round-trip: read → write → read
# ===========================================================================


class TestRoundTrip:

    def test_round_trip_preserves_data(self):
        """Data read from JSONL and written back produces identical records."""
        original = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob",   "email": "bob@example.com"},
        ]
        handler = JSONLHandler()

        source = make_jsonl_stream(*original)
        records = list(handler.read(source))

        dest = io.StringIO()
        handler.write(iter(records), dest)

        result = read_jsonl(dest)
        assert result == original

    def test_round_trip_with_unicode(self):
        """Unicode data survives a full read → write cycle."""
        original = [{"city": "Ouagadougou"}, {"name": "Aminata Traoré"}]
        handler = JSONLHandler()

        source = make_jsonl_stream(*original)
        records = list(handler.read(source))
        dest = io.StringIO()
        handler.write(iter(records), dest)

        result = read_jsonl(dest)
        assert result == original

    def test_round_trip_skips_malformed_lines(self, caplog):
        """Malformed lines are dropped during read, round-trip yields valid records only."""
        buf = io.StringIO('{"a": 1}\nbad line\n{"b": 2}\n')
        handler = JSONLHandler()

        with caplog.at_level(logging.WARNING, logger="maskme.io.jsonl_handler"):
            records = list(handler.read(buf))

        dest = io.StringIO()
        handler.write(iter(records), dest)
        result = read_jsonl(dest)
        assert result == [{"a": 1}, {"b": 2}]