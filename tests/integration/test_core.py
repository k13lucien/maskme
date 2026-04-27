from maskme.core import MaskMe

def test_core_hashing_integration():
    """Test if MaskMe correctly applies hashing to a nested path."""
    rules = {"user.id": "hash"}
    data = [{"user": {"id": "12345"}}]
    
    engine = MaskMe(rules, salt="test_salt")
    result = next(engine.mask(data))
    
    assert result["user"]["id"] != "12345"
    assert len(result["user"]["id"]) == 64