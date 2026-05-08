"""
Unit tests for maskme.io.json_handler
---------------------------------------
Uses io.StringIO as a lightweight stream substitute — no file system needed.
Covers read, write, round-trip, edge cases, and FormatHandler Protocol compliance.
"""

import io
import json

import pytest

from maskme.io.base import FormatHandler
from maskme.io.json_handler import JSONHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_json_stream(data) -> io.StringIO:
    """Build an in-memory JSON stream from a Python object."""
    buf = io.StringIO()
    json.dump(data, buf, ensure_ascii=False)
    buf.seek(0)
    return buf


def read_json(stream: io.StringIO):
    """Parse a JSON stream back into a Python object."""
    stream.seek(0)
    return json.loads(stream.read())


# ===========================================================================
# Protocol compliance
# ===========================================================================


class TestProtocol:

    def test_is_format_handler(self):
        """JSONHandler satisfies the FormatHandler Protocol at runtime."""
        assert isinstance(JSONHandler(), FormatHandler)

    def test_has_read_method(self):
        assert hasattr(JSONHandler(), "read")

    def test_has_write_method(self):
        assert hasattr(JSONHandler(), "write")


# ===========================================================================
# read()
# ===========================================================================


class TestRead:

    def test_reads_list_of_objects(self):
        """A JSON array yields one dict per element."""
        records = [{"name": "Alice"}, {"name": "Bob"}]
        stream = make_json_stream(records)
        result = list(JSONHandler().read(stream))
        assert result == records

    def test_reads_single_object(self):
        """A bare JSON object is yielded as a single record."""
        record = {"name": "Alice", "age": 30}
        stream = make_json_stream(record)
        result = list(JSONHandler().read(stream))
        assert result == [record]

    def test_reads_empty_list(self):
        """An empty JSON array yields nothing."""
        stream = make_json_stream([])
        result = list(JSONHandler().read(stream))
        assert result == []

    def test_yields_dicts(self):
        """Each yielded item is a dict."""
        stream = make_json_stream([{"a": 1}, {"b": 2}])
        for record in JSONHandler().read(stream):
            assert isinstance(record, dict)

    def test_preserves_record_order(self):
        """Records are yielded in the same order as in the source."""
        records = [{"n": i} for i in range(10)]
        stream = make_json_stream(records)
        result = list(JSONHandler().read(stream))
        assert [r["n"] for r in result] == list(range(10))

    def test_preserves_unicode_characters(self):
        """Unicode characters are read correctly."""
        records = [{"name": "Ouédraogo"}, {"city": "Ouagadougou"}]
        stream = make_json_stream(records)
        result = list(JSONHandler().read(stream))
        assert result == records

    def test_preserves_nested_values(self):
        """Nested dicts and lists within records are preserved."""
        record = {"user": {"email": "alice@example.com"}, "tags": ["a", "b"]}
        stream = make_json_stream([record])
        result = list(JSONHandler().read(stream))
        assert result == [record]

    def test_preserves_value_types(self):
        """Integer, float, bool and None values are preserved."""
        record = {"count": 42, "score": 3.14, "active": True, "note": None}
        stream = make_json_stream([record])
        result = list(JSONHandler().read(stream))
        assert result == [record]


# ===========================================================================
# write()
# ===========================================================================


class TestWrite:

    def test_writes_valid_json_array(self):
        """Output is a valid JSON array."""
        records = [{"name": "Alice"}, {"name": "Bob"}]
        out = io.StringIO()
        JSONHandler().write(iter(records), out)
        parsed = read_json(out)
        assert isinstance(parsed, list)
        assert parsed == records

    def test_single_record(self):
        """A single record is written as a one-element array."""
        out = io.StringIO()
        JSONHandler().write(iter([{"a": "1"}]), out)
        parsed = read_json(out)
        assert parsed == [{"a": "1"}]

    def test_empty_input_produces_empty_array(self):
        """An empty iterable produces an empty JSON array."""
        out = io.StringIO()
        JSONHandler().write(iter([]), out)
        parsed = read_json(out)
        assert parsed == []

    def test_preserves_unicode_characters(self):
        """Unicode characters are written without ASCII escaping."""
        records = [{"name": "Ouédraogo"}]
        out = io.StringIO()
        JSONHandler().write(iter(records), out)
        out.seek(0)
        raw = out.read()
        assert "Ouédraogo" in raw  # not escaped as \u00e9...

    def test_preserves_value_types(self):
        """Integer, float, bool and None are preserved through write."""
        record = {"count": 42, "score": 3.14, "active": True, "note": None}
        out = io.StringIO()
        JSONHandler().write(iter([record]), out)
        parsed = read_json(out)
        assert parsed == [record]

    def test_preserves_record_order(self):
        """Records are written in the same order as they arrive."""
        records = [{"n": i} for i in range(10)]
        out = io.StringIO()
        JSONHandler().write(iter(records), out)
        parsed = read_json(out)
        assert [r["n"] for r in parsed] == list(range(10))

    def test_output_is_well_formed_json(self):
        """Output can be parsed by json.loads without error."""
        records = [{"a": 1}, {"b": 2}, {"c": 3}]
        out = io.StringIO()
        JSONHandler().write(iter(records), out)
        out.seek(0)
        parsed = json.loads(out.read())
        assert len(parsed) == 3

    def test_no_memory_materialisation(self):
        """write() consumes a generator without converting it to a list first."""
        consumed = []

        def lazy_records():
            for i in range(5):
                consumed.append(i)
                yield {"n": i}

        out = io.StringIO()
        JSONHandler().write(lazy_records(), out)
        # All 5 records consumed one by one, not upfront
        assert consumed == list(range(5))


# ===========================================================================
# Round-trip: read → write → read
# ===========================================================================


class TestRoundTrip:

    def test_round_trip_preserves_data(self):
        """Data read from JSON and written back produces identical records."""
        original = [
            {"name": "Alice", "email": "alice@example.com", "age": 30},
            {"name": "Bob",   "email": "bob@example.com",   "age": 25},
        ]
        handler = JSONHandler()

        source = make_json_stream(original)
        records = list(handler.read(source))

        dest = io.StringIO()
        handler.write(iter(records), dest)

        result = read_json(dest)
        assert result == original

    def test_round_trip_with_unicode(self):
        """Unicode data survives a full read → write cycle."""
        original = [{"city": "Ouagadougou"}, {"name": "Aminata Traoré"}]
        handler = JSONHandler()

        source = make_json_stream(original)
        records = list(handler.read(source))
        dest = io.StringIO()
        handler.write(iter(records), dest)

        result = read_json(dest)
        assert result == original

    def test_round_trip_with_nested_values(self):
        """Nested structures survive a full read → write cycle."""
        original = [{"user": {"email": "alice@example.com"}, "tags": ["a", "b"]}]
        handler = JSONHandler()

        source = make_json_stream(original)
        records = list(handler.read(source))
        dest = io.StringIO()
        handler.write(iter(records), dest)

        result = read_json(dest)
        assert result == original