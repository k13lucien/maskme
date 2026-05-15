"""
maskme.utility
~~~~~~~~~~~~~~
Public API for the data utility measurement layer.

Usage:

    from maskme.utility import run
    from maskme.utility import report

    results = run(
        original=original_records,
        anonymised=anonymised_records,
        numerical_fields=["age", "salary"],
        categorical_fields=["gender", "zip_code", "diagnosis"],
    )

    report.generate(
        results=results,
        output_path="utility_report.html",
        dataset_info={"records": 5000, "source": "patients.csv"},
    )

Adding a new metric:
    1. Create  utility/metrics/<name>.py  implementing the Metric Protocol
    2. Import the class below and add it to METRICS
    → run() and report.py adapt automatically.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import report
from maskme.analytics.utility.metrics.base import Metric, UtilityResult
from maskme.analytics.utility.metrics.field_retention import FieldRetention
from maskme.analytics.utility.metrics.information_loss import InformationLoss
from maskme.analytics.utility.metrics.statistical_fidelity import StatisticalFidelity

# ---------------------------------------------------------------------------
# Registry — single source of truth for available utility metrics.
# ---------------------------------------------------------------------------

METRICS: Dict[str, Metric] = {
    "field_retention":      FieldRetention(),
    "statistical_fidelity": StatisticalFidelity(),
    "information_loss":     InformationLoss(),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
    numerical_fields: Optional[List[str]] = None,
    categorical_fields: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    field_retention_threshold:      float = 0.5,
    statistical_fidelity_threshold: float = 0.6,
    information_loss_threshold:     float = 0.5,
    **kwargs: Any,
) -> List[UtilityResult]:
    """
    Run one or more utility metrics and return results with charts attached.

    Args:
        original:           The original dataset before anonymization.
        anonymised:         The anonymised dataset produced by MaskMe.mask().
        numerical_fields:   Explicitly declared numerical field names.
                            Auto-detected from original if not provided.
        categorical_fields: Explicitly declared categorical field names.
                            Auto-detected from original if not provided.
        metrics:            Names of metrics to run. Defaults to all
                            registered metrics when None.
                            Valid keys: "field_retention",
                            "statistical_fidelity", "information_loss".
        field_retention_threshold:      Min acceptable retention score.
        statistical_fidelity_threshold: Min acceptable fidelity score.
        information_loss_threshold:     Min acceptable utility score (1-ILI).
        **kwargs:           Extra keyword arguments forwarded to every
                            metric's compute() method.

    Returns:
        List of UtilityResult instances, one per metric, in registry order.
        Each result has its charts already populated.

    Raises:
        ValueError: If an unknown metric name is requested.
        ValueError: If datasets are empty or have different lengths.
    """
    if not original:
        raise ValueError("Cannot run utility metrics on an empty dataset.")

    selected_names = metrics or list(METRICS.keys())
    unknown = [n for n in selected_names if n not in METRICS]
    if unknown:
        raise ValueError(
            f"Unknown metric(s): {unknown}. "
            f"Available: {list(METRICS.keys())}"
        )

    thresholds = {
        "field_retention":      field_retention_threshold,
        "statistical_fidelity": statistical_fidelity_threshold,
        "information_loss":     information_loss_threshold,
    }

    shared_kwargs = dict(
        numerical_fields=numerical_fields,
        categorical_fields=categorical_fields,
        **kwargs,
    )

    results = []
    for name in selected_names:
        metric = METRICS[name]
        result = metric.compute(
            original,
            anonymised,
            threshold=thresholds.get(name, 0.5),
            **shared_kwargs,
        )
        result.charts = metric.chart(result.summary)
        results.append(result)

    return results


__all__ = ["METRICS", "run", "report", "UtilityResult", "Metric"]