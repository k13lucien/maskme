import pytest
import numpy as np
from maskme.strategies.noise import apply

def test_noise_apply_basic_change():
    """
    Test that the value is actually modified by noise.
    """
    original_value = 100.0
    masked_value = apply(original_value, sigma=1.0)
    assert masked_value != original_value
    assert isinstance(masked_value, float)

def test_noise_deterministic_with_seed():
    """
    Test that the same seed produces the same noise for consistency.
    """
    val = 500.0
    seed = "user_123"
    result1 = apply(val, sigma=2.0, seed=seed)
    result2 = apply(val, sigma=2.0, seed=seed)
    assert result1 == result2

def test_noise_clipping_bounds():
    """
    Test that min_val and max_val constraints are strictly respected.
    """
    val = 10.0
    # Large sigma to force extreme values
    masked = apply(val, sigma=100.0, min_val=5.0, max_val=15.0)
    assert 5.0 <= masked <= 15.0

def test_noise_precision_control():
    """
    Test that the output matches the requested decimal precision.
    """
    val = 10.55678
    # Test rounding to 2 decimal places
    masked_2 = apply(val, sigma=1.0, precision=2)
    assert len(str(masked_2).split('.')[1]) <= 2
    
    # Test rounding to integer (precision=0)
    masked_int = apply(val, sigma=1.0, precision=0)
    assert isinstance(masked_int, int)

def test_noise_statistical_distribution():
    """
    Test that over a large sample, the noise is centered around zero.
    This validates the core Gaussian logic (Mean preservation).
    """
    original_value = 1000.0
    sigma = 10.0
    samples = [apply(original_value, sigma=sigma) for _ in range(5000)]
    
    mean_result = np.mean(samples)
    # The mean of noise N(0, sigma) should be very close to 0
    # so the result mean should be close to the original value
    assert 999.0 <= mean_result <= 1001.0

def test_noise_non_numeric_fallback():
    """
    Test that the strategy handles non-numeric inputs gracefully.
    """
    assert apply("not_a_number") == "not_a_number"
    assert apply(None) is None