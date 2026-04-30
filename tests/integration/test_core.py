from maskme.core import MaskMe
from maskme.analytics.metrics import evaluate_masking

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

def test_full_noise_pipeline_integration():
    """
    Integration test: 
    Rules -> Masking Engine -> Noise Strategy -> Analytics.
    """
    # 1. Setup rules
    rules = {
        "user.salary": {
            "strategy": "noise",
            "sigma": 50.0,
            "min_val": 1000.0,
            "precision": 2,
            "seed": 42
        }
    }
    
    # 2. Prepare dataset
    data = [
        {"user": {"salary": 3000.0}},
        {"user": {"salary": 3500.0}},
        {"user": {"salary": 4000.0}}
    ]
    
    # 3. Execute Masking
    engine = MaskMe(rules)
    masked_data = list(engine.mask(data))
    
    # 4. Extract values for analytics
    original_values = [d["user"]["salary"] for d in data]
    masked_values = [d["user"]["salary"] for d in masked_data]
    
    # 5. Validate through Analytics
    report = evaluate_masking(original_values, masked_values)
    
    # Verifications
    assert len(masked_values) == 3
    assert masked_values[0] != 3000.0
    assert report["utility_score"] > 0.9  # Should stay statistically close
    assert report["efficiency_score"] > 0 # Should have been altered