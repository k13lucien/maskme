import pytest
from maskme.strategies.hashing import apply

def test_hashing_basic():
    """Test standard hashing with default parameters."""
    result = apply("secret_data")
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 length in hex

def test_hashing_with_salt():
    """Ensure that different salts produce different hashes."""
    hash_a = apply("data", salt="salt_a")
    hash_b = apply("data", salt="salt_b")
    assert hash_a != hash_b

def test_hashing_algorithms():
    """Check if switching algorithm works and changes output length."""
    sha256_result = apply("data", algo="sha256")
    sha512_result = apply("data", algo="sha512")
    
    assert len(sha256_result) == 64
    assert len(sha512_result) == 128
    assert sha256_result != sha512_result

def test_hashing_none_value():
    """Ensure None values are handled gracefully."""
    assert apply(None) == ""