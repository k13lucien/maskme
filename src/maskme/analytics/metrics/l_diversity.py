"""
maskme.analytics.metrics.l_diversity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
l-diversity risk metric.

Reference:
    Machanavajjhala, A., Kifer, D., Gehrke, J. & Venkitasubramaniam, M.
    (2007). l-Diversity: Privacy Beyond k-Anonymity. ACM Transactions on
    Knowledge Discovery from Data, 1(1), Article 3.

Definition:
    A dataset satisfies distinct l-diversity if every equivalence class
    (as defined by k-anonymity) contains at least l distinct values for
    the sensitive attribute.

    Formally, for each equivalence class EC:
        |{t[sensitive] : t ∈ EC}| >= l

Relation to k-anonymity:
    l-diversity is a strictly stronger requirement than k-anonymity.
    A dataset that satisfies l-diversity also satisfies k-anonymity
    (with k ≤ l), but not vice versa.

    k-anonymity prevents linking attacks (who is this record?).
    l-diversity additionally prevents attribute disclosure attacks
    (what is this person's sensitive value?).

Limitations of distinct l-diversity:
    Does not account for the distribution of sensitive values within a
    class.  A class with l distinct values but one dominant value
    (e.g. 99 "benign" and 1 "cancer") technically satisfies l-diversity
    but still leaks the sensitive attribute.  For stronger guarantees,
    consider entropy l-diversity or t-closeness.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

from maskme.analytics.base import Analytic, AnalyticResult
from maskme.analytics.metrics._utils import build_equivalence_classes
from maskme.analytics import visual as v


class LDiversity:
    """
    Distinct l-diversity risk analytic.

    Evaluates whether every equivalence class contains a sufficient
    number of distinct values for a given sensitive attribute.
    """

    name = "l-Diversity"

    def compute(
        self,
        records: List[Dict[str, Any]],
        quasi_identifiers: List[str],
        sensitive_attr: str,
        l_threshold: int = 2,
        **kwargs: Any,
    ) -> AnalyticResult:
        """
        Evaluate distinct l-diversity over a dataset.

        Args:
            records:           The dataset as a list of dicts.
            quasi_identifiers: Fields that form the quasi-identifier.
            sensitive_attr:    The sensitive field to protect
                               (e.g. "diagnosis", "salary").
            l_threshold:       Minimum number of distinct sensitive values
                               required per equivalence class.
                               Defaults to 2.
            **kwargs:          Ignored (forwarded by the analytics runner).

        Returns:
            AnalyticResult with l-diversity metrics and per-class details.

        Raises:
            ValueError: If records is empty, quasi_identifiers is empty,
                        or sensitive_attr is not present in any record.
        """
        if not records:
            raise ValueError("Cannot compute l-diversity on an empty dataset.")
        if not quasi_identifiers:
            raise ValueError("At least one quasi-identifier must be provided.")
        if sensitive_attr not in records[0]:
            raise ValueError(
                f"Sensitive attribute '{sensitive_attr}' not found in records."
            )

        classes = build_equivalence_classes(records, quasi_identifiers)

        # Per-class distinct sensitive value counts
        class_stats = _compute_class_stats(classes, sensitive_attr)
        diversity_values = [s["distinct_count"] for s in class_stats.values()]

        total_records   = len(records)
        num_classes     = len(classes)
        l_min           = min(diversity_values)
        l_max           = max(diversity_values)
        l_mean          = round(sum(diversity_values) / num_classes, 2)

        at_risk_classes = sum(
            1 for v in diversity_values if v < l_threshold
        )
        at_risk_records = sum(
            stats["class_size"]
            for stats in class_stats.values()
            if stats["distinct_count"] < l_threshold
        )
        pct_at_risk = round(100 * at_risk_records / total_records, 2)

        # Distribution: {distinct_count: number_of_classes}
        diversity_dist = dict(Counter(diversity_values))

        passed = l_min >= l_threshold

        details = sorted(
            [
                {
                    "quasi_identifiers": dict(zip(quasi_identifiers, key)),
                    "class_size":        stats["class_size"],
                    "distinct_values":   stats["distinct_count"],
                    "value_distribution": stats["value_distribution"],
                    "satisfies_l":       stats["distinct_count"] >= l_threshold,
                }
                for key, stats in class_stats.items()
            ],
            key=lambda d: d["distinct_values"],
        )

        summary = {
            "l_min":             l_min,
            "l_max":             l_max,
            "l_mean":            l_mean,
            "l_threshold":       l_threshold,
            "num_classes":       num_classes,
            "at_risk_classes":   at_risk_classes,
            "total_records":     total_records,
            "at_risk_records":   at_risk_records,
            "pct_at_risk":       pct_at_risk,
            "passed":            passed,
            "diversity_distribution": diversity_dist,
        }

        recommendations = _build_recommendations(
            passed, l_min, l_threshold, pct_at_risk,
            at_risk_classes, sensitive_attr,
        )

        return AnalyticResult(
            name=self.name,
            passed=passed,
            summary=summary,
            details=details,
            recommendations=recommendations,
            threshold=l_threshold,
            metadata={
                "quasi_identifiers": quasi_identifiers,
                "sensitive_attr":    sensitive_attr,
                "variant":           "distinct l-diversity",
                "reference":         "Machanavajjhala et al. (2007)",
            },
        )

    def chart(self, summary: Dict[str, Any]) -> List[str]:
        """
        Generate a bar chart of distinct sensitive values per class.

        Bars are coloured red for counts below l_threshold, green otherwise.
        A dashed vertical line marks the threshold boundary.
        """
        dist      : Dict[int, int] = summary.get("diversity_distribution", {})
        threshold : int            = summary.get("l_threshold", 2)

        if not dist:
            return [v.svg_open("l-Diversity")
                    + v.text(v.W / 2, v.H / 2, "No data available.")
                    + v.svg_close()]

        values         = sorted(dist.keys())
        counts         = [dist[val] for val in values]
        y_max          = v.nice_max(max(counts))
        bar_w, bar_gap = v.bar_layout(len(values))

        svg  = v.svg_open("l-Diversity — Sensitive Value Distribution")
        svg += v.draw_title(
            "l-Diversity — Distinct Sensitive Values per Class",
            f"Threshold l ≥ {threshold}  ·  "
            f"l_min = {summary.get('l_min')}  ·  "
            f"{summary.get('at_risk_classes', 0)} class(es) at risk",
        )
        svg += v.draw_axes(y_max, "Number of classes",
                           "Distinct sensitive values per class")

        for i, (val, count) in enumerate(zip(values, counts)):
            x     = v.ML + i * bar_gap + (bar_gap - bar_w) / 2
            h     = (count / y_max) * v.PH
            y     = v.MT + v.PH - h
            color = v.COLOR_RISK if val < threshold else v.COLOR_SAFE
            svg  += v.bar(x, y, bar_w, h, color)
            svg  += v.text(x + bar_w / 2, y - 5, str(count),
                           size=9, color=v.COLOR_SUBTEXT)
            svg  += v.label_x(x + bar_w / 2, v.MT + v.PH + 16, str(val))

        t_idx = next((i for i, val in enumerate(values) if val >= threshold),
                     None)
        if t_idx is not None:
            svg += v.vline(v.ML + t_idx * bar_gap, f"l = {threshold}")

        lx   = v.ML + v.PW - 195
        svg += v.legend_item(lx,       v.MT + 10, v.COLOR_SAFE,
                             "Satisfies l-diversity")
        svg += v.legend_item(lx + 160, v.MT + 10, v.COLOR_RISK, "At risk")
        svg += v.svg_close()
        return [svg]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_class_stats(
    classes: Dict[Tuple, List[Dict[str, Any]]],
    sensitive_attr: str,
) -> Dict[Tuple, Dict[str, Any]]:
    """
    Compute per-class diversity statistics for the sensitive attribute.

    Returns:
        Dict mapping each class key to:
            class_size         — number of records in the class
            distinct_count     — number of distinct sensitive values
            value_distribution — {value: count} within the class
    """
    stats = {}
    for key, members in classes.items():
        values = [str(r.get(sensitive_attr, "")) for r in members]
        dist = dict(Counter(values))
        stats[key] = {
            "class_size":         len(members),
            "distinct_count":     len(dist),
            "value_distribution": dist,
        }
    return stats


def _build_recommendations(
    passed: bool,
    l_min: int,
    l_threshold: int,
    pct_at_risk: float,
    at_risk_classes: int,
    sensitive_attr: str,
) -> List[str]:
    """Generate actionable recommendations based on l-diversity results."""
    recs = []

    if not passed:
        recs.append(
            f"The dataset does NOT satisfy {l_threshold}-diversity "
            f"(l_min = {l_min}). Attribute disclosure is possible for "
            f"records in {at_risk_classes} equivalence class(es) "
            f"({pct_at_risk}% of records)."
        )
        recs.append(
            f"Equivalence classes with fewer than {l_threshold} distinct "
            f"'{sensitive_attr}' values allow an adversary to infer the "
            "sensitive attribute with high confidence. Consider merging "
            "small classes or suppressing the sensitive attribute for "
            "under-diverse groups."
        )
        if l_min == 1:
            recs.append(
                "Classes with a single distinct sensitive value fully expose "
                f"'{sensitive_attr}' for all their members. These classes "
                "must be restructured before publishing."
            )
    else:
        recs.append(
            f"The dataset satisfies {l_threshold}-diversity (l_min = {l_min}). "
            f"Every equivalence class contains at least {l_min} distinct "
            f"value(s) of '{sensitive_attr}'."
        )

    recs.append(
        "Note: distinct l-diversity does not account for value distribution "
        "within classes. A skewed distribution (e.g. one rare sensitive "
        "value among many identical ones) may still leak information. "
        "Consider t-closeness for stronger guarantees."
    )

    return recs