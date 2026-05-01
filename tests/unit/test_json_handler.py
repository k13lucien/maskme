import pytest
import io
import json
from maskme.io.json_handler import JSONHandler

def test_json_handler_read_list():
    """
    Test that JSONHandler correctly reads a standard JSON list and yields dicts.
    """
    json_content = json.dumps([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ])
    input_stream = io.StringIO(json_content)
    
    handler = JSONHandler()
    records = list(handler.read(input_stream))
    
    assert len(records) == 2
    assert records[0]["name"] == "Alice"
    assert records[1]["id"] == 2

def test_json_handler_read_single_object():
    """
    Ensure the handler can handle a single JSON object (not in a list).
    """
    json_content = json.dumps({"id": 1, "name": "Alice"})
    input_stream = io.StringIO(json_content)
    
    handler = JSONHandler()
    records = list(handler.read(input_stream))
    
    assert len(records) == 1
    assert records[0]["name"] == "Alice"

def test_json_handler_write():
    """
    Test that JSONHandler writes a collection of dicts as a valid JSON list.
    """
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
    output_stream = io.StringIO()
    
    handler = JSONHandler()
    handler.write(records, output_stream)
    
    # Parse back to verify structure
    result = json.loads(output_stream.getvalue())
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[1]["name"] == "Bob"

def test_json_handler_invalid_format():
    """
    Check behavior when providing invalid JSON.
    """
    input_stream = io.StringIO("{ invalid json }")
    handler = JSONHandler()
    
    with pytest.raises(json.JSONDecodeError):
        list(handler.read(input_stream))