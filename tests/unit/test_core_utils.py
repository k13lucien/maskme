import pytest
from maskme.core import MaskMe

def test_get_nested_logic():
    """Test the dot notation retrieval logic."""
    engine = MaskMe(rules={})
    data = {"a": {"b": {"c": 42}}}
    assert engine._get_nested(data, "a.b.c") == 42
    assert engine._get_nested(data, "a.z") is None

def test_set_nested_logic():
    """Test the dot notation assignment logic."""
    engine = MaskMe(rules={})
    data = {}
    engine._set_nested(data, "a.b.c", 100)
    assert data["a"]["b"]["c"] == 100