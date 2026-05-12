"""
maskme.analytics.metrics.k_anonymity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
k-anonymity risk metric.

Reference:
    Samarati, P. & Sweeney, L. (1998). Protecting Privacy when Disclosing
    Information: k-Anonymity and Its Enforcement through Generalization
    and Suppression. Technical Report, SRI International.

Definition:
    A dataset satisfies k-anonymity with respect to a set of quasi-
    identifiers (QIs) if every record is indistinguishable from at least
    k-1 other records based on the QI values alone.

    Formally, for each record r, the equivalence class EC(r) — the set of
    all records sharing r's QI values — must satisfy |EC(r)| >= k.

Risk interpretation:
    A record in an equivalence class of size s carries a re-identification
    risk of 1/s. Smaller classes → higher risk. Singleton classes (s=1)
    guarantee re-identification.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

from maskme.analytics.base import Analytic, AnalyticResult
from maskme.analytics.metrics._utils import build_equivalence_classes
from maskme.analytics import visual as v


def _class_size_distribution(
    classes: Dict[Tuple, List],
) -> Dict[int, int]:
    """
    Count how many equivalence classes have each size.

    Returns:
        {class_size: number_of_classes_with_that_size}
    """
    return dict(Counter(len(members) for members in classes.values()))


class KAnonymity:
    """
    k-anonymity risk analytic.

    Computes equivalence classes over quasi-identifiers and measures
    whether every class meets the minimum size threshold k.
    """

    name = "k-Anonymity"

    def compute(
        self,
        records: List[Dict[str, Any]],
        quasi_identifiers: List[str],
        k_threshold: int = 2,
        **kwargs: Any,
    ) -> AnalyticResult:
        """
        Evaluate k-anonymity over a dataset.

        Args:
            records:           The dataset as a list of dicts.
            quasi_identifiers: Fields that form the quasi-identifier
                               (e.g. ["age", "zip_code", "gender"]).
            k_threshold:       Minimum acceptable equivalence class size.
                               The dataset passes if k_min >= k_threshold.
                               Defaults to 2.
            **kwargs:          Ignored (forwarded by the analytics runner).

        Returns:
            AnalyticResult with k-anonymity metrics and per-class details.

        Raises:
            ValueError: If records is empty or quasi_identifiers is empty.
        """
        if not records:
            raise ValueError("Cannot compute k-anonymity on an empty dataset.")
        if not quasi_identifiers:
            raise ValueError("At least one quasi-identifier must be provided.")

        classes = build_equivalence_classes(records, quasi_identifiers)
        sizes = [len(members) for members in classes.values()]

        total_records  = len(records)
        num_classes    = len(classes)
        k_min          = min(sizes)
        k_max          = max(sizes)
        k_mean         = sum(sizes) / num_classes
        k_median       = sorted(sizes)[num_classes // 2]
        size_dist      = _class_size_distribution(classes)

        # Records in classes that violate the threshold
        at_risk_records = sum(
            len(members)
            for members in classes.values()
            if len(members) < k_threshold
        )
        pct_at_risk = round(100 * at_risk_records / total_records, 2)

        passed = k_min >= k_threshold

        # Per-class details (sorted by class size ascending for readability)
        details = sorted(
            [
                {
                    "quasi_identifiers":  dict(zip(quasi_identifiers, key)),
                    "class_size":         len(members),
                    "risk":               round(1 / len(members), 4),
                    "satisfies_k":        len(members) >= k_threshold,
                }
                for key, members in classes.items()
            ],
            key=lambda d: d["class_size"],
        )

        recommendations = _build_recommendations(
            passed, k_min, k_threshold, pct_at_risk, at_risk_records
        )

        summary = {
            "k_min":           k_min,
            "k_max":           k_max,
            "k_mean":          round(k_mean, 2),
            "k_median":        k_median,
            "k_threshold":     k_threshold,
            "num_classes":     num_classes,
            "total_records":   total_records,
            "at_risk_records": at_risk_records,
            "pct_at_risk":     pct_at_risk,
            "passed":          passed,
            "size_distribution": size_dist,
        }

        return AnalyticResult(
            name=self.name,
            passed=passed,
            summary=summary,
            details=details,
            recommendations=recommendations,
            threshold=k_threshold,
            metadata={
                "quasi_identifiers": quasi_identifiers,
                "reference": "Samarati & Sweeney (1998)",
            },
        )

    def chart(self, summary: Dict[str, Any]) -> List[str]:
        """
        Generate a bar chart of equivalence class size distribution.

        Bars are coloured red for sizes below k_threshold, green otherwise.
        A dashed vertical line marks the threshold boundary.
        """
        dist      : Dict[int, int] = summary.get("size_distribution", {})
        threshold : int            = summary.get("k_threshold", 2)

        if not dist:
            return [v.svg_open("k-Anonymity")
                    + v.text(v.W / 2, v.H / 2, "No data available.")
                    + v.svg_close()]

        sizes          = sorted(dist.keys())
        counts         = [dist[s] for s in sizes]
        y_max          = v.nice_max(max(counts))
        bar_w, bar_gap = v.bar_layout(len(sizes))

        svg  = v.svg_open("k-Anonymity — Class Size Distribution")
        svg += v.draw_title(
            "k-Anonymity — Equivalence Class Size Distribution",
            f"Threshold k ≥ {threshold}  ·  "
            f"k_min = {summary.get('k_min')}  ·  "
            f"{summary.get('at_risk_records', 0)} record(s) at risk",
        )
        svg += v.draw_axes(y_max, "Number of classes", "Equivalence class size")

        for i, (size, count) in enumerate(zip(sizes, counts)):
            x     = v.ML + i * bar_gap + (bar_gap - bar_w) / 2
            h     = (count / y_max) * v.PH
            y     = v.MT + v.PH - h
            color = v.COLOR_RISK if size < threshold else v.COLOR_SAFE
            svg  += v.bar(x, y, bar_w, h, color)
            svg  += v.text(x + bar_w / 2, y - 5, str(count),
                           size=9, color=v.COLOR_SUBTEXT)
            svg  += v.label_x(x + bar_w / 2, v.MT + v.PH + 16, str(size))

        # Dashed vertical threshold marker
        t_idx = next((i for i, s in enumerate(sizes) if s >= threshold), None)
        if t_idx is not None:
            svg += v.vline(v.ML + t_idx * bar_gap, f"k = {threshold}")

        lx   = v.ML + v.PW - 195
        svg += v.legend_item(lx,       v.MT + 10, v.COLOR_SAFE,
                             "Satisfies k-anonymity")
        svg += v.legend_item(lx + 160, v.MT + 10, v.COLOR_RISK, "At risk")
        svg += v.svg_close()
        return [svg]


def _build_recommendations(
    passed: bool,
    k_min: int,
    k_threshold: int,
    pct_at_risk: float,
    at_risk_records: int,
) -> List[str]:
    """Generate actionable recommendations based on k-anonymity results."""
    recs = []

    if not passed:
        recs.append(
            f"The dataset does NOT satisfy {k_threshold}-anonymity "
            f"(k_min = {k_min}). Re-identification is possible for "
            f"{at_risk_records} record(s) ({pct_at_risk}% of the dataset)."
        )
        recs.append(
            "Apply stronger generalization to quasi-identifiers in small "
            "equivalence classes, or suppress records that cannot be grouped."
        )
        if k_min == 1:
            recs.append(
                "Singleton equivalence classes detected (k=1): these records "
                "are directly re-identifiable. Consider removing or heavily "
                "generalizing their quasi-identifier values."
            )
    else:
        recs.append(
            f"The dataset satisfies {k_threshold}-anonymity (k_min = {k_min}). "
            "Every record is indistinguishable from at least "
            f"{k_min - 1} other(s)."
        )
        if k_min == k_threshold:
            recs.append(
                f"k_min equals the threshold ({k_threshold}). Consider "
                "increasing the threshold for stronger privacy guarantees."
            )

    if pct_at_risk > 0 and passed:
        recs.append(
            f"{pct_at_risk}% of records are in equivalence classes below "
            f"the threshold of {k_threshold}. Monitor these groups closely."
        )

    return recs