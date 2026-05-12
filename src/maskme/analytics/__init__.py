"""
maskme.analytics
~~~~~~~~~~~~~~~~
Public API for the re-identification risk analytics layer.

Usage:

    from maskme.analytics import run, ANALYTICS

    # Run all registered analytics
    results = run(
        records=anonymised_records,
        quasi_identifiers=["age", "zip_code", "gender"],
        sensitive_attr="diagnosis",
        k_threshold=3,
        l_threshold=2,
        t_threshold=0.2,
    )

    # Run a specific subset
    results = run(
        records=records,
        analytics=["k_anonymity", "t_closeness"],
        quasi_identifiers=["age", "zip_code"],
        sensitive_attr="salary",
    )

    # Generate HTML report
    from maskme.analytics import report
    report.generate(results, output_path="risk_report.html")

Adding a new analytic:
    1. Create  analytics/metrics/<name>.py  implementing Analytic Protocol
    2. Import the class below and add it to ANALYTICS
    → run(), report.py, and visual.py adapt automatically.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from maskme.analytics.base import Analytic, AnalyticResult
from maskme.analytics.metrics.k_anonymity import KAnonymity
from maskme.analytics.metrics.l_diversity import LDiversity
from maskme.analytics.metrics.t_closeness import TCloseness

# ---------------------------------------------------------------------------
# Registry — single source of truth for available analytics.
# Keys are stable identifiers used to select analytics by name.
# ---------------------------------------------------------------------------

ANALYTICS: Dict[str, Analytic] = {
    "k_anonymity": KAnonymity(),
    "l_diversity": LDiversity(),
    "t_closeness": TCloseness(),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(
    records: List[Dict[str, Any]],
    quasi_identifiers: List[str],
    sensitive_attr: str,
    analytics: Optional[List[str]] = None,
    k_threshold: int   = 2,
    l_threshold: int   = 2,
    t_threshold: float = 0.2,
    **kwargs: Any,
) -> List[AnalyticResult]:
    """
    Run one or more analytics and return their results with charts attached.

    Args:
        records:           The anonymised dataset as a list of dicts.
        quasi_identifiers: Fields that form the quasi-identifier
                           (e.g. ["age", "zip_code", "gender"]).
        sensitive_attr:    The sensitive field to protect
                           (e.g. "diagnosis", "salary").
        analytics:         Names of analytics to run. Defaults to all
                           registered analytics when None.
                           Valid keys: "k_anonymity", "l_diversity",
                           "t_closeness".
        k_threshold:       Minimum equivalence class size for k-anonymity.
        l_threshold:       Minimum distinct sensitive values for l-diversity.
        t_threshold:       Maximum EMD per class for t-closeness.
        **kwargs:          Extra keyword arguments forwarded to every
                           analytic's compute() method.

    Returns:
        List of AnalyticResult instances, one per analytic, in registry
        order. Each result has its charts already populated.

    Raises:
        ValueError: If an unknown analytic name is requested.
        ValueError: If records is empty or quasi_identifiers is empty.
    """
    if not records:
        raise ValueError("Cannot run analytics on an empty dataset.")
    if not quasi_identifiers:
        raise ValueError("At least one quasi-identifier must be provided.")

    # Resolve which analytics to run
    selected_names = analytics or list(ANALYTICS.keys())
    unknown = [n for n in selected_names if n not in ANALYTICS]
    if unknown:
        raise ValueError(
            f"Unknown analytic(s): {unknown}. "
            f"Available: {list(ANALYTICS.keys())}"
        )

    # Shared kwargs forwarded to every analytic
    shared_kwargs = dict(
        quasi_identifiers=quasi_identifiers,
        sensitive_attr=sensitive_attr,
        k_threshold=k_threshold,
        l_threshold=l_threshold,
        t_threshold=t_threshold,
        **kwargs,
    )

    results = []
    for name in selected_names:
        analytic = ANALYTICS[name]
        result   = analytic.compute(records, **shared_kwargs)

        # Each analytic generates its own charts via chart()
        result.charts = analytic.chart(result.summary)

        results.append(result)

    return results


__all__ = ["ANALYTICS", "run", "AnalyticResult", "Analytic"]