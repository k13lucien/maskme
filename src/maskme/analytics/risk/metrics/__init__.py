"""
maskme.analytics.risk.metrics
~~~~~~~~~~~~~~~~~~~~~~~~
Individual re-identification risk analytics.

    Each module implements the Metric Protocol defined in risk/base.py.
    To add a new metric, create a new file here and register it in
    risk/__init__.py under METRICS.
"""

from maskme.analytics.risk.metrics.k_anonymity import KAnonymity
from maskme.analytics.risk.metrics.l_diversity import LDiversity
from maskme.analytics.risk.metrics.t_closeness import TCloseness

__all__ = ["KAnonymity", "LDiversity", "TCloseness"]