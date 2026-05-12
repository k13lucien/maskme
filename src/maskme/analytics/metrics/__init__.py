"""
maskme.analytics.metrics
~~~~~~~~~~~~~~~~~~~~~~~~
Individual re-identification risk analytics.

Each module implements the Analytic Protocol defined in analytics/base.py.
To add a new metric, create a new file here and register it in
analytics/__init__.py under ANALYTICS.
"""

from maskme.analytics.metrics.k_anonymity import KAnonymity
from maskme.analytics.metrics.l_diversity import LDiversity
from maskme.analytics.metrics.t_closeness import TCloseness

__all__ = ["KAnonymity", "LDiversity", "TCloseness"]