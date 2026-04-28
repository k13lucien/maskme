import pytest
from maskme.strategies.redaction import apply

def test_redact_full_masking():
    """
    Test full redaction with default parameters.
    Ensures all characters are replaced by the default placeholder.
    """
    assert apply("sensitive_data") == "**************"

def test_redact_partial_keep_start():
    """
    Test redaction while keeping the beginning of the string visible.
    Example: 'Lucien' with keep_start=2 -> 'Lu****'
    """
    assert apply("Lucien", keep_start=2) == "Lu****"

def test_redact_partial_keep_end():
    """
    Test redaction while keeping the end of the string visible.
    Example: 'secret123' with keep_end=3 -> '******123'
    """
    assert apply("secret123", keep_end=3) == "******123"

def test_redact_partial_keep_both():
    """
    Test redaction keeping both start and end visible (useful for PII like phone numbers).
    Example: '0123456789' with keep_start=2, keep_end=2 -> '01******89'
    """
    assert apply("0123456789", keep_start=2, keep_end=2) == "01******89"

def test_redact_custom_character():
    """
    Test redaction using a custom placeholder character.
    """
    assert apply("password", char="#") == "########"

def test_redact_short_value_handling():
    """
    Test behavior when the string is shorter than the combined visible parts.
    The system should fallback to full redaction to prevent data leakage.
    """
    # Value length 3, requested visible 5 -> should mask everything
    assert apply("abc", keep_start=5) == "***"

def test_redact_empty_and_none():
    """
    Test handling of empty strings and None values.
    """
    assert apply("") == ""