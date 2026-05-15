"""
maskme.analytics
~~~~~~~~~~~~~~~~
Public API for the masking analytics layer.

Two sub-packages:
    risk     — Re-identification risk analytics
               (k-anonymity, l-diversity, t-closeness)
    utility  — Data utility measurement
               (field retention, statistical fidelity, information loss)
"""

from maskme.analytics import risk
from maskme.analytics import utility

__all__ = ["risk", "utility"]
