import pytest
import io
from maskme.io.csv_handler import CSVHandler

def test_csv_handler_read():
    """
    Test that CSVHandler correctly converts CSV strings into dictionaries.
    """
    csv_content = "id,name,city\n1,Alice,Paris\n2,Bob,Lyon"
    # io.StringIO simulates a file in memory
    input_stream = io.StringIO(csv_content)
    
    handler = CSVHandler()
    records = list(handler.read(input_stream))
    
    assert len(records) == 2
    assert records[0]["name"] == "Alice"
    assert records[1]["city"] == "Lyon"
    assert "id" in records[0]

def test_csv_handler_write():
    """
    Test that CSVHandler correctly writes dictionaries back to a CSV format.
    """
    records = [
        {"id": "1", "name": "Alice", "city": "Paris"},
        {"id": "2", "name": "Bob", "city": "Lyon"}
    ]
    output_stream = io.StringIO()
    
    handler = CSVHandler()
    handler.write(records, output_stream)
    
    result = output_stream.getvalue()
    
    # Check headers and content
    assert "id,name,city" in result
    assert "1,Alice,Paris" in result
    assert "2,Bob,Lyon" in result

def test_csv_handler_empty_input():
    """
    Ensure the handler handles empty streams gracefully.
    """
    input_stream = io.StringIO("")
    handler = CSVHandler()
    records = list(handler.read(input_stream))
    
    assert records == []

def test_csv_handler_write_empty_list():
    """
    Ensure writing an empty list of records doesn't crash.
    """
    output_stream = io.StringIO()
    handler = CSVHandler()
    handler.write([], output_stream)
    
    assert output_stream.getvalue() == ""