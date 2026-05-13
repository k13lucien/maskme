"""
maskme.utility.metrics.statistical_fidelity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Statistical Fidelity metric.

Compares the statistical properties of the original and anonymised
datasets field by field, distinguishing numerical and categorical fields.

Numerical fields:
    - Δmean       : normalised absolute difference in means
    - Δstd        : normalised absolute difference in standard deviations
    - Spearman ρ  : rank correlation preserving the monotonic relationship
                    between original and anonymised values
    - Fidelity    : 1 - Δmean (clamped to [0, 1])

Categorical fields:
    - TVD         : Total Variation Distance between frequency distributions
                    TVD = ½ · Σ|p_i − q_i| ∈ [0, 1]
    - Fidelity    : 1 - TVD

Global score: simple average of per-field fidelity scores.

Chart: grouped before/after bar chart showing mean values for numerical
       fields, and TVD bars for categorical fields.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from maskme.analytics import visual as v
from maskme.utility.base import Metric, UtilityResult
from maskme.utility.metrics._utils import (
    classify_fields,
    paired_values,
    safe_float,
    validate_alignment,
)


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu  = _mean(values)
    var = sum((x - mu) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def _spearman(xs: List[float], ys: List[float]) -> float:
    """
    Spearman rank correlation coefficient.

    Measures the monotonic relationship between original and anonymised
    numerical values. ρ = 1 → perfect monotonic preservation,
    ρ = -1 → reversed, ρ = 0 → no correlation.

    Uses the standard formula:
        ρ = 1 - (6 · Σd²) / (n · (n² - 1))
    where d = rank(x) - rank(y).
    """
    n = len(xs)
    if n < 2:
        return 1.0

    def _ranks(vals: List[float]) -> List[float]:
        sorted_idx = sorted(range(n), key=lambda i: vals[i])
        ranks      = [0.0] * n
        for rank, idx in enumerate(sorted_idx, start=1):
            ranks[idx] = float(rank)
        return ranks

    rx = _ranks(xs)
    ry = _ranks(ys)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - (6 * d2) / (n * (n ** 2 - 1)) if n > 1 else 1.0


def _tvd(orig_counts: Dict[str, int],
         anon_counts: Dict[str, int],
         n_orig: int, n_anon: int) -> float:
    """
    Total Variation Distance between two categorical distributions.

        TVD = ½ · Σ|p_i − q_i|

    Returns a value in [0, 1] where 0 = identical distributions.
    """
    all_vals = set(orig_counts) | set(anon_counts)
    return 0.5 * sum(
        abs(orig_counts.get(v, 0) / n_orig - anon_counts.get(v, 0) / n_anon)
        for v in all_vals
    )


def _normalised_delta(orig: float, anon: float, scale: float) -> float:
    """Normalised absolute difference, clamped to [0, 1]."""
    if scale == 0:
        return 0.0
    return min(abs(orig - anon) / scale, 1.0)


# ---------------------------------------------------------------------------
# Per-field analysis
# ---------------------------------------------------------------------------

def _analyse_numerical(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
    field: str,
) -> Dict[str, Any]:
    """Compute statistical fidelity metrics for a numerical field."""
    pairs = paired_values(original, anonymised, field)

    orig_vals = [safe_float(o) for o, _ in pairs if safe_float(o) is not None]
    anon_vals = [safe_float(a) for _, a in pairs if safe_float(a) is not None]

    if not orig_vals or not anon_vals:
        return {"fidelity": 0.0, "error": "no numeric values found"}

    orig_mean = _mean(orig_vals)
    anon_mean = _mean(anon_vals)
    orig_std  = _std(orig_vals)
    anon_std  = _std(anon_vals)

    # Scale for normalisation: original range or std, whichever is larger
    orig_range = max(orig_vals) - min(orig_vals) if len(orig_vals) > 1 else 1.0
    scale      = max(orig_range, abs(orig_mean), 1e-9)

    delta_mean = _normalised_delta(orig_mean, anon_mean, scale)
    delta_std  = _normalised_delta(orig_std,  anon_std,  max(orig_std, 1e-9))

    # Spearman on paired values only (both non-None)
    paired_num = [
        (safe_float(o), safe_float(a))
        for o, a in pairs
        if safe_float(o) is not None and safe_float(a) is not None
    ]
    spearman = (
        _spearman([p[0] for p in paired_num], [p[1] for p in paired_num])
        if len(paired_num) >= 2 else 1.0
    )

    fidelity = round(max(0.0, 1.0 - delta_mean), 4)

    return {
        "type":         "numerical",
        "orig_mean":    round(orig_mean, 4),
        "anon_mean":    round(anon_mean, 4),
        "orig_std":     round(orig_std, 4),
        "anon_std":     round(anon_std, 4),
        "delta_mean":   round(delta_mean, 4),
        "delta_std":    round(delta_std, 4),
        "spearman_rho": round(spearman, 4),
        "fidelity":     fidelity,
        "n_orig":       len(orig_vals),
        "n_anon":       len(anon_vals),
    }


def _analyse_categorical(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
    field: str,
) -> Dict[str, Any]:
    """Compute statistical fidelity metrics for a categorical field."""
    pairs = paired_values(original, anonymised, field)

    orig_vals = [o for o, _ in pairs if o is not None]
    anon_vals = [a for _, a in pairs if a is not None]

    if not orig_vals or not anon_vals:
        return {"fidelity": 0.0, "error": "no values found"}

    orig_counts = Counter(orig_vals)
    anon_counts = Counter(anon_vals)

    tvd      = round(_tvd(orig_counts, anon_counts,
                          len(orig_vals), len(anon_vals)), 4)
    fidelity = round(max(0.0, 1.0 - tvd), 4)

    return {
        "type":            "categorical",
        "tvd":             tvd,
        "fidelity":        fidelity,
        "orig_top_value":  orig_counts.most_common(1)[0][0],
        "anon_top_value":  anon_counts.most_common(1)[0][0],
        "orig_unique":     len(orig_counts),
        "anon_unique":     len(anon_counts),
        "n_orig":          len(orig_vals),
        "n_anon":          len(anon_vals),
    }


# ---------------------------------------------------------------------------
# Metric class
# ---------------------------------------------------------------------------

class StatisticalFidelity:
    """
    Compares the statistical properties of original and anonymised datasets.
    """

    name = "Statistical Fidelity"

    def compute(
        self,
        original: List[Dict[str, Any]],
        anonymised: List[Dict[str, Any]],
        numerical_fields: Optional[List[str]] = None,
        categorical_fields: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> UtilityResult:
        """
        Evaluate statistical fidelity across all fields.

        Args:
            original:           Original dataset.
            anonymised:         Anonymised dataset.
            numerical_fields:   Explicitly declared numerical fields.
                                Auto-detected if not provided.
            categorical_fields: Explicitly declared categorical fields.
                                Auto-detected if not provided.
            **kwargs:           Ignored (forwarded by the utility runner).

        Returns:
            UtilityResult with per-field fidelity scores and global score.

        Raises:
            ValueError: If datasets are empty or have different lengths.
        """
        if not original:
            raise ValueError(
                "Cannot compute statistical fidelity on an empty dataset."
            )
        validate_alignment(original, anonymised)

        num_fields, cat_fields = classify_fields(
            original, numerical_fields, categorical_fields
        )

        per_field: Dict[str, Dict] = {}

        for field in num_fields:
            per_field[field] = _analyse_numerical(original, anonymised, field)

        for field in cat_fields:
            per_field[field] = _analyse_categorical(original, anonymised, field)

        fidelities   = [s["fidelity"] for s in per_field.values()
                        if "error" not in s]
        global_score = round(sum(fidelities) / len(fidelities), 4) \
                       if fidelities else 0.0

        low_fidelity = [
            f for f, s in per_field.items()
            if s.get("fidelity", 1.0) < 0.5 and "error" not in s
        ]

        summary = {
            "global_fidelity_score": global_score,
            "numerical_fields":      num_fields,
            "categorical_fields":    cat_fields,
            "low_fidelity_fields":   low_fidelity,
            "per_field":             per_field,
        }

        details = sorted(
            [
                {
                    "field":    field,
                    "type":     stats.get("type", "unknown"),
                    "fidelity": stats.get("fidelity", 0.0),
                    **{k: v for k, v in stats.items()
                       if k not in ("type", "fidelity", "error")},
                }
                for field, stats in per_field.items()
            ],
            key=lambda d: d["fidelity"],
        )

        threshold = kwargs.get("threshold", 0.6)
        passed    = global_score >= threshold

        recommendations = _build_recommendations(
            global_score, low_fidelity, per_field, threshold
        )

        return UtilityResult(
            name=self.name,
            score=global_score,
            passed=passed,
            summary=summary,
            details=details,
            recommendations=recommendations,
            threshold=threshold,
            metadata={
                "numerical_fields":   num_fields,
                "categorical_fields": cat_fields,
            },
        )

    def chart(self, summary: Dict[str, Any]) -> List[str]:
        """
        Two charts:
        1. Grouped before/after mean bars for numerical fields.
        2. TVD bars for categorical fields.
        """
        charts = []
        per_field = summary.get("per_field", {})

        num_stats = {
            f: s for f, s in per_field.items()
            if s.get("type") == "numerical" and "error" not in s
        }
        cat_stats = {
            f: s for f, s in per_field.items()
            if s.get("type") == "categorical" and "error" not in s
        }

        if num_stats:
            charts.append(_chart_numerical(num_stats))
        if cat_stats:
            charts.append(_chart_categorical(cat_stats))

        return charts


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _chart_numerical(num_stats: Dict[str, Dict]) -> str:
    """Grouped before/after mean bar chart for numerical fields."""
    fields   = list(num_stats.keys())
    n        = len(fields)
    y_max    = v.nice_max(max(
        max(s["orig_mean"], s["anon_mean"]) for s in num_stats.values()
    ) * 1.1)

    group_w  = v.PW / n
    bar_w    = min(group_w * 0.35, 30)

    svg  = v.svg_open("Statistical Fidelity — Numerical Means")
    svg += v.draw_title(
        "Statistical Fidelity — Mean Comparison (Numerical Fields)",
        "Green = original · Blue = anonymised",
    )
    svg += v.draw_axes(y_max, "Mean value", "Field")

    for i, field in enumerate(fields):
        s      = num_stats[field]
        gx     = v.ML + i * group_w + group_w / 2

        # Original bar
        h_orig = (s["orig_mean"] / y_max) * v.PH if y_max else 0
        x_orig = gx - bar_w - 2
        svg   += v.bar(x_orig, v.MT + v.PH - h_orig, bar_w, h_orig, v.COLOR_SAFE)

        # Anonymised bar
        h_anon = (s["anon_mean"] / y_max) * v.PH if y_max else 0
        x_anon = gx + 2
        svg   += v.bar(x_anon, v.MT + v.PH - h_anon, bar_w, h_anon, "#3B82F6")

        svg += v.label_x(gx, v.MT + v.PH + 16, field)

        # Fidelity label
        svg += v.text(gx, v.MT + v.PH + 28,
                      f"ρ={s['fidelity']:.2f}",
                      size=9, color=v.COLOR_SUBTEXT)

    lx   = v.ML + v.PW - 180
    svg += v.legend_item(lx,       v.MT + 10, v.COLOR_SAFE, "Original mean")
    svg += v.legend_item(lx + 130, v.MT + 10, "#3B82F6",    "Anonymised mean")
    svg += v.svg_close()
    return svg


def _chart_categorical(cat_stats: Dict[str, Dict]) -> str:
    """TVD bar chart for categorical fields — lower is better."""
    fields  = list(cat_stats.keys())
    n       = len(fields)
    tvds    = [cat_stats[f]["tvd"] for f in fields]
    y_max   = v.nice_max(max(tvds) * 1.1) if tvds else 1.0

    bar_w, bar_gap = v.bar_layout(n)

    svg  = v.svg_open("Statistical Fidelity — Categorical TVD")
    svg += v.draw_title(
        "Statistical Fidelity — Distribution Distance (Categorical Fields)",
        "Total Variation Distance per field — lower is better",
    )
    svg += v.draw_axes(y_max, "TVD", "Field")

    for i, field in enumerate(fields):
        tvd   = cat_stats[field]["tvd"]
        x     = v.ML + i * bar_gap + (bar_gap - bar_w) / 2
        h     = (tvd / y_max) * v.PH if y_max else 0
        y     = v.MT + v.PH - h
        color = v.COLOR_RISK if tvd > 0.5 else (
                v.COLOR_THRESHOLD if tvd > 0.2 else v.COLOR_SAFE)
        svg  += v.bar(x, y, bar_w, h, color)
        svg  += v.text(x + bar_w / 2, y - 5, f"{tvd:.2f}",
                       size=9, color=v.COLOR_SUBTEXT)
        svg  += v.label_x(x + bar_w / 2, v.MT + v.PH + 16, field)

    svg += v.hline(0.2, y_max, "TVD = 0.2")
    svg += v.svg_close()
    return svg


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _build_recommendations(
    global_score: float,
    low_fidelity: List[str],
    per_field: Dict[str, Dict],
    threshold: float,
) -> List[str]:
    recs = []

    pct = round(global_score * 100, 1)

    if global_score >= 0.8:
        recs.append(
            f"Global statistical fidelity is {pct}% — the anonymised "
            "dataset closely mirrors the statistical properties of the "
            "original. Aggregate analyses should remain reliable."
        )
    elif global_score >= 0.5:
        recs.append(
            f"Global statistical fidelity is {pct}%. Some fields show "
            "significant distributional drift. Validate statistical "
            "analyses field by field before publishing results."
        )
    else:
        recs.append(
            f"Global statistical fidelity is only {pct}%. The anonymised "
            "dataset's statistical properties diverge substantially from "
            "the original. Aggregate statistics, ML models trained on "
            "this data, and trend analyses may be unreliable."
        )

    if low_fidelity:
        recs.append(
            f"Field(s) with fidelity < 50%: {', '.join(low_fidelity)}. "
            "Consider lighter anonymization strategies (e.g. noise instead "
            "of redaction) for these fields if re-identification risk allows."
        )

    # Spearman warnings for numerical fields
    low_spearman = [
        f for f, s in per_field.items()
        if s.get("type") == "numerical"
        and s.get("spearman_rho", 1.0) < 0.5
        and "error" not in s
    ]
    if low_spearman:
        recs.append(
            f"Field(s) {', '.join(low_spearman)} show low Spearman rank "
            "correlation (ρ < 0.5). The ordering of values is not preserved "
            "— ranking-based analyses will be affected."
        )

    # High TVD warnings for categorical fields
    high_tvd = [
        f for f, s in per_field.items()
        if s.get("type") == "categorical"
        and s.get("tvd", 0.0) > 0.5
        and "error" not in s
    ]
    if high_tvd:
        recs.append(
            f"Field(s) {', '.join(high_tvd)} have a Total Variation Distance "
            "> 0.5. Frequency-based analyses (mode, proportions, chi-square "
            "tests) on these fields will yield misleading results."
        )

    return recs