"""
maskme
~~~~~~
Agnostic data anonymization engine.

Quick usage:

    from maskme import MaskMe

    rules = {
        "user.email": "hash",
        "user.phone": {"strategy": "mask", "char": "*"},
        "user.ssn":   "drop",
    }
    engine = MaskMe(rules=rules, salt="my-secret")
    anonymized = list(engine.mask(records))
"""

from maskme.core.engine import MaskMe

__all__ = ["MaskMe"]