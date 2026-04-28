import pytest
import numpy as np
from maskme.analytics.metrics import evaluate_masking

def test_evaluate_masking_perfect_utility():
    """
    Test metrics when original and masked data are identical.
    Utility should be 1.0 and efficiency (noise) should be 0.0.
    """
    original = [10, 20, 30, 40, 50]
    masked = [10, 20, 30, 40, 50]
    
    report = evaluate_masking(original, masked)
    
    assert report["utility_score"] == 1.0
    assert report["efficiency_score"] == 0.0
    assert report["mean_drift"] == 0.0

def test_evaluate_masking_with_known_noise():
    """
    Test metrics with a controlled shift to verify MAE and Drift.
    """
    original = [100, 200, 300]
    # Add exactly +10 to each value
    masked = [110, 210, 310]
    
    report = evaluate_masking(original, masked)
    
    # Efficiency (MAE) should be 10.0
    assert report["efficiency_score"] == 10.0
    # Mean drift should be 10.0
    assert report["mean_drift"] == 10.0
    # Utility (variance ratio) should be 1.0 since spread didn't change
    assert report["utility_score"] == 1.0

def test_evaluate_masking_variance_loss():
    """
    Test utility score when data becomes more 'flat' (loss of variance).
    """
    original = [10, 20, 30] # Var = 66.66
    masked = [19, 20, 21]   # Var = 0.66 (Lower spread)
    
    report = evaluate_masking(original, masked)
    
    # Utility score should be significantly lower than 1.0
    assert report["utility_score"] < 0.1

def test_evaluate_masking_handling_empty():
    """
    Ensures the analytics module doesn't crash with empty input.
    """
    with pytest.raises((ValueError, ZeroDivisionError)):
        evaluate_masking([], [])

def test_evaluate_masking_mismatched_length():
    """Ensures a ValueError is raised if lengths differ."""
    with pytest.raises(ValueError, match="must have the same length"):
        evaluate_masking([1, 2], [1])