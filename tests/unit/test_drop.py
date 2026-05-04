import pytest
from maskme.core.engine import MaskMe

def test_drop_strategy_simple_field():
    """
    Test that a top-level field is completely removed from the dictionary.
    """
    rules = {"ssn": "drop"}
    data = [
        {"id": 1, "name": "Alice", "ssn": "123-456-789"},
        {"id": 2, "name": "Bob", "ssn": "987-654-321"}
    ]
    
    engine = MaskMe(rules)
    # Convert generator to list for assertions
    masked_data = list(engine.mask(data))
    
    # Assertions
    assert "ssn" not in masked_data[0]
    assert "ssn" not in masked_data[1]
    assert masked_data[0]["name"] == "Alice"
    assert len(masked_data[0]) == 2  # Only 'id' and 'name' should remain

def test_drop_strategy_nested_field():
    """
    Test field removal within nested structures using dot notation.
    """
    rules = {"user.internal_id": "drop"}
    data = [
        {
            "user": {
                "name": "Lucien",
                "internal_id": "UUID-999",
                "public_id": "PUB-1"
            }
        }
    ]
    
    engine = MaskMe(rules)
    masked_data = list(engine.mask(data))
    
    # Nested object should still exist, but without the dropped key
    assert "user" in masked_data[0]
    assert "internal_id" not in masked_data[0]["user"]
    assert masked_data[0]["user"]["public_id"] == "PUB-1"

def test_drop_non_existent_field():
    """
    Ensure the engine handles missing fields gracefully without raising errors.
    """
    rules = {"missing_key": "drop"}
    data = [{"id": 1, "name": "Alice"}]
    
    engine = MaskMe(rules)
    masked_data = list(engine.mask(data))
    
    # Data should remain unchanged
    assert masked_data[0] == {"id": 1, "name": "Alice"}

def test_mixed_strategies_with_drop():
    """
    Verify that 'drop' works correctly alongside other strategies like 'hash' and 'keep'.
    """
    rules = {
        "id": "hash",
        "ssn": "drop",
        "symptom": "keep"
    }
    data = [{"id": "123", "ssn": "SECRET-01", "symptom": "Flu"}]
    
    engine = MaskMe(rules)
    result = list(engine.mask(data))[0]
    
    assert "ssn" not in result
    assert result["id"] != "123"  # Should be hashed
    assert result["symptom"] == "Flu"  # Should be preserved