"""
maskme.utility.metrics
~~~~~~~~~~~~~~~~~~~~~~~
Individual data utility metrics.

Each module implements the Metric Protocol defined in utility/base.py.
To add a new metric, create a new file here and register it in
utility/__init__.py under METRICS.
"""

from maskme.utility.metrics.field_retention import FieldRetention
from maskme.utility.metrics.information_loss import InformationLoss
from maskme.utility.metrics.statistical_fidelity import StatisticalFidelity
from maskme.utility.metrics import run

__all__ = ["FieldRetention", "run", "StatisticalFidelity", "InformationLoss"]