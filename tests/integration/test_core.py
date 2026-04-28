from maskme.core import MaskMe

def test_core_hashing_integration():
    """Test if MaskMe correctly applies hashing to a nested path."""
    rules = {"user.id": "hash"}
    data = [{"user": {"id": "12345"}}]
    
    engine = MaskMe(rules, salt="test_salt")
    result = next(engine.mask(data))
    
    assert result["user"]["id"] != "12345"
    assert len(result["user"]["id"]) == 64

def test_core_redaction_integration():
    """
    Test if MaskMe correctly applies redaction to a nested path.
    This ensures the 'core' engine can pass parameters to the 'redaction' strategy.
    """
    rules = {
        "user.email": {
            "strategy": "redact",
            "keep_start": 1,
            "keep_end": 4
        }
    }
    data = [{"user": {"email": "lucien@example.com"}}]
    
    engine = MaskMe(rules)
    result = next(engine.mask(data))
    
    # Expected: 'l' + '***********' + '.com'
    assert result["user"]["email"] != "lucien@example.com"
    assert result["user"]["email"].startswith("l")
    assert result["user"]["email"].endswith(".com")
    assert "*" in result["user"]["email"]