import pytest
import io
import json
from maskme.io.jsonl_handler import JSONLHandler

def test_jsonl_handler_read():
    """
    Check if JSONLHandler correctly parses each line as a separate JSON object.
    """
    # Including empty lines to test robustness
    jsonl_content = '{"id": 1, "task": "clean"}\n{"id": 2, "task": "mask"}\n\n'
    input_stream = io.StringIO(jsonl_content)
    
    handler = JSONLHandler()
    records = list(handler.read(input_stream))
    
    assert len(records) == 2
    assert records[0]["task"] == "clean"
    assert records[1]["id"] == 2

def test_jsonl_handler_write():
    """
    Verify that JSONLHandler writes objects line by line without global brackets.
    """
    records = [
        {"user": "admin", "action": "login"},
        {"user": "guest", "action": "view"}
    ]
    output_stream = io.StringIO()
    
    handler = JSONLHandler()
    handler.write(records, output_stream)
    
    result = output_stream.getvalue()
    lines = result.strip().split('\n')
    
    assert len(lines) == 2
    # Verify each line is a valid independent JSON
    assert json.loads(lines[0])["user"] == "admin"
    assert json.loads(lines[1])["action"] == "view"

def test_jsonl_handler_read_invalid_line():
    """
    Ensure the handler raises an error when encountering malformed JSON on a line.
    """
    jsonl_content = '{"id": 1}\n{invalid: json}\n{"id": 3}'
    input_stream = io.StringIO(jsonl_content)
    
    handler = JSONLHandler()
    iterator = handler.read(input_stream)
    
    # First line should pass
    assert next(iterator)["id"] == 1
    # Second line should raise an error during iteration
    with pytest.raises(json.JSONDecodeError):
        next(iterator)