"""
maskme.analytics.risk.metrics.t_closeness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
t-closeness risk metric.

Reference:
    Li, N., Li, T. & Venkatasubramanian, S. (2007). t-Closeness: Privacy
    Beyond k-Anonymity and l-Diversity. Proceedings of the 23rd IEEE
    International Conference on Data Engineering (ICDE), pp. 106-115.

Definition:
    An equivalence class satisfies t-closeness if the distance between
    the distribution of the sensitive attribute within the class and the
    overall distribution in the full dataset is no more than t.

    A dataset satisfies t-closeness if all its equivalence classes do.

    Formally, for each equivalence class EC:
        EMD(P_EC, P_global) <= t

    Where EMD is the Earth Mover's Distance (also called Wasserstein-1
    distance), measuring the minimum "work" to transform one distribution
    into another.

Two EMD variants (auto-detected from attribute type):

    Categorical (unordered) attributes — Total Variation Distance:
        EMD(P, Q) = ½ · Σᵢ |pᵢ − qᵢ|
        Range: [0, 1].  0 = identical distributions, 1 = disjoint.

    Numerical (ordered) attributes — Cumulative Distribution distance:
        EMD(P, Q) = 1/(m−1) · Σᵢ₌₁ᵐ⁻¹ |CDF_class(vᵢ) − CDF_global(vᵢ)|
        Where values are sorted ascending and m is the number of unique
        values.  Accounts for the ordering of the domain.
        Reference: Li et al. (2007), Section 3.2.

Relation to k-anonymity and l-diversity:
    t-closeness is the strictest of the three models.  It addresses the
    skewness attack and the similarity attack that l-diversity cannot
    prevent.  A class with l distinct sensitive values but a highly
    skewed distribution (one dominant value) may violate t-closeness
    even while satisfying l-diversity.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from maskme.analytics.risk.metrics.base import Metric, RiskResult
from maskme.analytics.risk.metrics._utils import build_equivalence_classes
from maskme.analytics import visual as v


# ---------------------------------------------------------------------------
# EMD computation
# ---------------------------------------------------------------------------

def _is_numerical(values: List[str]) -> bool:
    """Return True if all non-empty values can be cast to float."""
    for v in values:
        if v == "":
            continue
        try:
            float(v)
        except ValueError:
            return False
    return True


def _global_distribution(
    records: List[Dict[str, Any]],
    sensitive_attr: str,
) -> Dict[str, float]:
    """
    Compute the overall relative frequency distribution of the sensitive
    attribute across the full dataset.

    Returns:
        {value: relative_frequency}  — sums to 1.0.
    """
    counts = Counter(str(r.get(sensitive_attr, "")) for r in records)
    total = sum(counts.values())
    return {v: c / total for v, c in counts.items()}


def _emd_categorical(
    class_dist: Dict[str, float],
    global_dist: Dict[str, float],
) -> float:
    """
    Earth Mover's Distance for unordered (categorical) attributes.

    Uses Total Variation Distance:
        EMD(P, Q) = ½ · Σᵢ |pᵢ − qᵢ|

    Args:
        class_dist:  Relative frequency distribution within the class.
        global_dist: Overall relative frequency distribution.

    Returns:
        EMD in [0, 1].
    """
    all_values = set(class_dist) | set(global_dist)
    return 0.5 * sum(
        abs(class_dist.get(v, 0.0) - global_dist.get(v, 0.0))
        for v in all_values
    )


def _emd_numerical(
    class_dist: Dict[str, float],
    global_dist: Dict[str, float],
) -> float:
    """
    Earth Mover's Distance for ordered (numerical) attributes.

    Uses the cumulative distribution function (CDF) area difference:
        EMD(P, Q) = 1/(m−1) · Σᵢ₌₁ᵐ⁻¹ |CDF_class(vᵢ) − CDF_global(vᵢ)|

    Where values are sorted ascending and m is the number of unique values.
    Reference: Li et al. (2007), Section 3.2.

    Args:
        class_dist:  Relative frequency distribution within the class.
        global_dist: Overall relative frequency distribution.

    Returns:
        EMD in [0, 1], or 0.0 if there is only one unique value.
    """
    all_values = sorted(set(class_dist) | set(global_dist), key=float)
    m = len(all_values)
    if m <= 1:
        return 0.0

    cdf_class  = 0.0
    cdf_global = 0.0
    emd        = 0.0

    # Accumulate CDF difference over all but the last value
    for v in all_values[:-1]:
        cdf_class  += class_dist.get(v, 0.0)
        cdf_global += global_dist.get(v, 0.0)
        emd        += abs(cdf_class - cdf_global)

    return emd / (m - 1)


def _class_distribution(
    members: List[Dict[str, Any]],
    sensitive_attr: str,
) -> Dict[str, float]:
    """
    Compute the relative frequency distribution of the sensitive attribute
    within a single equivalence class.
    """
    counts = Counter(str(r.get(sensitive_attr, "")) for r in members)
    total  = sum(counts.values())
    return {v: c / total for v, c in counts.items()}


# ---------------------------------------------------------------------------
# Analytic class
# ---------------------------------------------------------------------------

class TCloseness:
    """
    t-closeness risk analytic.

    Measures the Earth Mover's Distance between the sensitive attribute
    distribution in each equivalence class and the global distribution.
    Auto-detects whether the attribute is categorical or numerical to
    apply the appropriate EMD formula.
    """

    name = "t-Closeness"

    def compute(
        self,
        records: List[Dict[str, Any]],
        quasi_identifiers: List[str],
        sensitive_attr: str,
        t_threshold: float = 0.2,
        **kwargs: Any,
    ) -> RiskResult:
        """
        Evaluate t-closeness over a dataset.

        Args:
            records:           The dataset as a list of dicts.
            quasi_identifiers: Fields that form the quasi-identifier.
            sensitive_attr:    The sensitive field to measure distribution
                               distance on (e.g. "salary", "diagnosis").
            t_threshold:       Maximum acceptable EMD per equivalence class.
                               Defaults to 0.2 (a common practical value).
            **kwargs:          Ignored (forwarded by the metrics runner).

        Returns:
            RiskResult with t-closeness metrics and per-class details.

        Raises:
            ValueError: If records is empty, quasi_identifiers is empty,
                        or sensitive_attr is absent from all records.
        """
        if not records:
            raise ValueError("Cannot compute t-closeness on an empty dataset.")
        if not quasi_identifiers:
            raise ValueError("At least one quasi-identifier must be provided.")
        if sensitive_attr not in records[0]:
            raise ValueError(
                f"Sensitive attribute '{sensitive_attr}' not found in records."
            )

        # Detect attribute type once — applies to all classes
        all_values = [str(r.get(sensitive_attr, "")) for r in records]
        numerical  = _is_numerical(all_values)
        emd_fn     = _emd_numerical if numerical else _emd_categorical
        attr_type  = "numerical" if numerical else "categorical"

        global_dist = _global_distribution(records, sensitive_attr)
        classes     = build_equivalence_classes(records, quasi_identifiers)

        # Per-class EMD computation
        class_results = {}
        for key, members in classes.items():
            c_dist = _class_distribution(members, sensitive_attr)
            emd    = round(emd_fn(c_dist, global_dist), 6)
            class_results[key] = {
                "class_size":         len(members),
                "emd":                emd,
                "satisfies_t":        emd <= t_threshold,
                "class_distribution": c_dist,
            }

        emd_values  = [v["emd"] for v in class_results.values()]
        total_records = len(records)
        num_classes   = len(classes)

        t_max  = round(max(emd_values), 6)
        t_min  = round(min(emd_values), 6)
        t_mean = round(sum(emd_values) / num_classes, 6)

        at_risk_records = sum(
            stats["class_size"]
            for stats in class_results.values()
            if not stats["satisfies_t"]
        )
        at_risk_classes = sum(
            1 for stats in class_results.values()
            if not stats["satisfies_t"]
        )
        pct_at_risk = round(100 * at_risk_records / total_records, 2)

        passed = t_max <= t_threshold

        details = sorted(
            [
                {
                    "quasi_identifiers":  dict(zip(quasi_identifiers, key)),
                    "class_size":         stats["class_size"],
                    "emd":                stats["emd"],
                    "satisfies_t":        stats["satisfies_t"],
                    "class_distribution": stats["class_distribution"],
                }
                for key, stats in class_results.items()
            ],
            key=lambda d: d["emd"],
            reverse=True,  # highest EMD (most at-risk) first
        )

        summary = {
            "t_max":           t_max,
            "t_min":           t_min,
            "t_mean":          t_mean,
            "t_threshold":     t_threshold,
            "num_classes":     num_classes,
            "at_risk_classes": at_risk_classes,
            "at_risk_records": at_risk_records,
            "total_records":   total_records,
            "pct_at_risk":     pct_at_risk,
            "passed":          passed,
            "attribute_type":  attr_type,
            "emd_values":      sorted(emd_values),
        }

        recommendations = _build_recommendations(
            passed, t_max, t_threshold, attr_type,
            at_risk_classes, pct_at_risk, sensitive_attr,
        )

        return RiskResult(
            name=self.name,
            passed=passed,
            summary=summary,
            details=details,
            recommendations=recommendations,
            threshold=t_threshold,
            metadata={
                "quasi_identifiers": quasi_identifiers,
                "sensitive_attr":    sensitive_attr,
                "attribute_type":    attr_type,
                "emd_formula":       (
                    "CDF area difference (Li et al. 2007 §3.2)"
                    if numerical else
                    "Total Variation Distance (½·Σ|pᵢ−qᵢ|)"
                ),
                "reference":         "Li, Li & Venkatasubramanian (2007)",
            },
        )

    def chart(self, summary: Dict[str, Any]) -> List[str]:
        """
        Generate a sorted bar chart of EMD values per equivalence class.

        Bars are sorted ascending by EMD. Red bars exceed t_threshold,
        green bars satisfy it. A dashed horizontal line marks the threshold.
        """
        emd_values : List[float] = sorted(summary.get("emd_values", []))
        threshold  : float       = summary.get("t_threshold", 0.2)
        attr_type  : str         = summary.get("attribute_type", "categorical")

        if not emd_values:
            return [v.svg_open("t-Closeness")
                    + v.text(v.W / 2, v.H / 2, "No data available.")
                    + v.svg_close()]

        y_max          = v.nice_max(max(max(emd_values), threshold) * 1.1)
        bar_w, bar_gap = v.bar_layout(len(emd_values), max_bar_w=40)
        bar_w          = max(bar_w, 2)

        svg  = v.svg_open("t-Closeness — EMD Distribution")
        svg += v.draw_title(
            "t-Closeness — Earth Mover's Distance per Class",
            f"Threshold t ≤ {threshold}  ·  "
            f"t_max = {summary.get('t_max')}  ·  "
            f"Type: {attr_type}  ·  "
            f"{summary.get('at_risk_classes', 0)} class(es) at risk",
        )
        svg += v.draw_axes(y_max, "EMD",
                           "Equivalence class (sorted by EMD ↑)")

        for i, emd in enumerate(emd_values):
            x     = v.ML + i * bar_gap + (bar_gap - bar_w) / 2
            h     = max((emd / y_max) * v.PH, 1)
            y     = v.MT + v.PH - h
            color = v.COLOR_RISK if emd > threshold else v.COLOR_SAFE
            svg  += v.bar(x, y, bar_w, h, color)

        svg += v.hline(threshold, y_max, f"t = {threshold}")

        lx   = v.ML + 10
        svg += v.legend_item(lx,       v.MT + 10, v.COLOR_SAFE,
                             "Satisfies t-closeness")
        svg += v.legend_item(lx + 160, v.MT + 10, v.COLOR_RISK,
                             "Exceeds threshold")
        svg += v.svg_close()
        return [svg]


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _build_recommendations(
    passed: bool,
    t_max: float,
    t_threshold: float,
    attr_type: str,
    at_risk_classes: int,
    pct_at_risk: float,
    sensitive_attr: str,
) -> List[str]:
    """Generate actionable recommendations based on t-closeness results."""
    recs = []

    if not passed:
        recs.append(
            f"The dataset does NOT satisfy t-closeness with t ≤ {t_threshold} "
            f"(t_max = {t_max}). The distribution of '{sensitive_attr}' in "
            f"{at_risk_classes} class(es) ({pct_at_risk}% of records) "
            "diverges significantly from the global distribution."
        )
        recs.append(
            "Apply stronger generalization or add noise to the sensitive "
            f"attribute '{sensitive_attr}' to reduce distributional skew "
            "within equivalence classes."
        )
        if t_max > 0.5:
            recs.append(
                f"t_max = {t_max} is critically high (> 0.5). Some equivalence "
                "classes have a sensitive attribute distribution almost entirely "
                "different from the global one, enabling near-certain attribute "
                "inference attacks."
            )
    else:
        recs.append(
            f"The dataset satisfies t-closeness with t ≤ {t_threshold} "
            f"(t_max = {t_max}). The distribution of '{sensitive_attr}' "
            "within every equivalence class is sufficiently close to the "
            "global distribution."
        )

    if attr_type == "numerical":
        recs.append(
            "Numerical attribute detected: EMD was computed using the ordered "
            "CDF distance (Li et al. 2007, §3.2), which accounts for the "
            "magnitude of differences between values."
        )
    else:
        recs.append(
            "Categorical attribute detected: EMD was computed using Total "
            "Variation Distance (½·Σ|pᵢ−qᵢ|), treating all values as "
            "unordered."
        )

    recs.append(
        f"Recommended t threshold range: 0.05–0.20 for strong privacy, "
        "0.20–0.50 for moderate utility/privacy trade-off. "
        f"Current threshold: {t_threshold}."
    )

    return recs