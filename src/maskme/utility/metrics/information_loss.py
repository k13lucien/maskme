"""
maskme.utility.metrics.information_loss
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Information Loss Index (ILI) metric.

Quantifies how much information was destroyed during anonymization,
expressed as a normalised score in [0, 1]:

    ILI = 0.0 → no information lost  (perfect utility)
    ILI = 1.0 → all information lost (complete destruction)

Utility score = 1 - ILI, consistent with the [0, 1] convention used
across all UtilityResult instances.

Per-field ILI computation:

    Numerical fields:
        Normalised Mean Absolute Error (NMAE):
            ILI = Σ|orig_i − anon_i| / (n · range(orig))
        Dropped values contribute the full range to the numerator.
        Range is floored at 1e-9 to avoid division by zero.

    Categorical fields:
        Proportion of values that changed (including dropped):
            ILI = (n_changed + n_dropped) / n_total
        A value that changed from "A" to "B" is counted once.
        A dropped value counts as fully lost.

    Fully dropped fields:
        ILI = 1.0 (all information lost).

Global ILI:
    Simple average of per-field ILIs, giving equal weight to each field.
    A weighted variant (by field cardinality or importance) can be added
    via the weights kwarg in future iterations.

Chart:
    Horizontal bar chart — one bar per field coloured by ILI level:
        green  (ILI ≤ 0.2)  — low loss, data still highly usable
        amber  (ILI ≤ 0.5)  — moderate loss
        red    (ILI > 0.5)  — high loss, field may not be reliable
    A global ILI gauge is rendered as a colour-coded arc above the bars.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from maskme.analytics import visual as v
from maskme.utility.base import Metric, UtilityResult
from maskme.utility.metrics._utils import (
    all_fields,
    classify_fields,
    paired_values,
    safe_float,
    validate_alignment,
    value_changed,
    value_dropped,
)


# ---------------------------------------------------------------------------
# Per-field ILI computation
# ---------------------------------------------------------------------------

def _ili_numerical(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
    field: str,
) -> Dict[str, Any]:
    """
    Compute ILI for a numerical field using Normalised MAE.

        ILI = Σ|orig_i − anon_i| / (n · range(orig))

    Dropped values (anon = None) are treated as maximum loss:
    they contribute range(orig) to the numerator.
    """
    pairs     = paired_values(original, anonymised, field)
    n         = len(pairs)

    orig_nums = [safe_float(o) for o, _ in pairs if safe_float(o) is not None]
    if not orig_nums:
        return {"ili": 1.0, "note": "no numeric values in original"}

    orig_range = max(orig_nums) - min(orig_nums) if len(orig_nums) > 1 else 1.0
    orig_range = max(orig_range, 1e-9)

    total_loss = 0.0
    n_dropped  = 0
    n_modified = 0
    n_unchanged = 0

    for o_str, a_str in pairs:
        o = safe_float(o_str)
        if o is None:
            continue  # field absent in original — skip

        if a_str is None:          # dropped
            total_loss += orig_range
            n_dropped  += 1
        else:
            a = safe_float(a_str)
            if a is None:          # became non-numeric after masking
                total_loss += orig_range
                n_modified += 1
            else:
                diff = abs(o - a)
                total_loss  += diff
                if diff > 1e-9:
                    n_modified += 1
                else:
                    n_unchanged += 1

    ili = min(total_loss / (n * orig_range), 1.0)

    return {
        "type":       "numerical",
        "ili":        round(ili, 4),
        "orig_range": round(orig_range, 4),
        "n_unchanged": n_unchanged,
        "n_modified":  n_modified,
        "n_dropped":   n_dropped,
    }


def _ili_categorical(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
    field: str,
) -> Dict[str, Any]:
    """
    Compute ILI for a categorical field.

        ILI = (n_changed + n_dropped) / n_total

    Any change in value — including hash, redact, generalize — is
    counted as full information loss for that record's field value.
    """
    pairs      = paired_values(original, anonymised, field)
    n          = len(pairs)
    n_dropped  = sum(1 for o, a in pairs if value_dropped(o, a))
    n_modified = sum(
        1 for o, a in pairs
        if not value_dropped(o, a) and value_changed(o, a)
    )
    n_unchanged = n - n_dropped - n_modified
    ili         = (n_dropped + n_modified) / n if n else 1.0

    return {
        "type":        "categorical",
        "ili":         round(ili, 4),
        "n_unchanged": n_unchanged,
        "n_modified":  n_modified,
        "n_dropped":   n_dropped,
    }


# ---------------------------------------------------------------------------
# Metric class
# ---------------------------------------------------------------------------

class InformationLoss:
    """
    Normalised Information Loss Index (ILI) per field and globally.

    Provides a single actionable number per field indicating how much
    information was destroyed, regardless of the anonymization strategy
    applied.
    """

    name = "Information Loss"

    def compute(
        self,
        original: List[Dict[str, Any]],
        anonymised: List[Dict[str, Any]],
        numerical_fields: Optional[List[str]] = None,
        categorical_fields: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> UtilityResult:
        """
        Compute the Information Loss Index for all fields.

        Args:
            original:           Original dataset.
            anonymised:         Anonymised dataset.
            numerical_fields:   Explicitly declared numerical fields.
            categorical_fields: Explicitly declared categorical fields.
            **kwargs:           Accepts threshold (float, default 0.5).

        Returns:
            UtilityResult where score = 1 - global_ILI.

        Raises:
            ValueError: If datasets are empty or have different lengths.
        """
        if not original:
            raise ValueError(
                "Cannot compute information loss on an empty dataset."
            )
        validate_alignment(original, anonymised)

        num_fields, cat_fields = classify_fields(
            original, numerical_fields, categorical_fields
        )

        per_field: Dict[str, Dict] = {}

        for field in num_fields:
            per_field[field] = _ili_numerical(original, anonymised, field)

        for field in cat_fields:
            per_field[field] = _ili_categorical(original, anonymised, field)

        ili_values   = [s["ili"] for s in per_field.values()]
        global_ili   = round(sum(ili_values) / len(ili_values), 4) \
                       if ili_values else 1.0
        score        = round(1.0 - global_ili, 4)   # utility = 1 - loss

        threshold    = kwargs.get("threshold", 0.5)  # min acceptable score
        passed       = score >= threshold

        high_loss    = [
            f for f, s in per_field.items() if s["ili"] > 0.5
        ]
        low_loss     = [
            f for f, s in per_field.items() if s["ili"] <= 0.2
        ]

        summary = {
            "global_ili":        global_ili,
            "utility_score":     score,
            "high_loss_fields":  high_loss,
            "low_loss_fields":   low_loss,
            "numerical_fields":  num_fields,
            "categorical_fields": cat_fields,
            "per_field":         per_field,
        }

        details = sorted(
            [
                {
                    "field":       field,
                    "type":        stats["type"],
                    "ili":         stats["ili"],
                    "n_unchanged": stats["n_unchanged"],
                    "n_modified":  stats["n_modified"],
                    "n_dropped":   stats["n_dropped"],
                    "loss_level":  (
                        "high"     if stats["ili"] > 0.5  else
                        "moderate" if stats["ili"] > 0.2  else
                        "low"
                    ),
                }
                for field, stats in per_field.items()
            ],
            key=lambda d: d["ili"],
            reverse=True,
        )

        recommendations = _build_recommendations(
            global_ili, score, high_loss, low_loss, per_field, threshold
        )

        return UtilityResult(
            name=self.name,
            score=score,
            passed=passed,
            summary=summary,
            details=details,
            recommendations=recommendations,
            threshold=threshold,
            metadata={
                "numerical_fields":   num_fields,
                "categorical_fields": cat_fields,
                "ili_formula": {
                    "numerical":   "NMAE = Σ|orig−anon| / (n·range)",
                    "categorical": "proportion of changed or dropped values",
                },
            },
        )

    def chart(self, summary: Dict[str, Any]) -> List[str]:
        """
        Two charts:
        1. Global ILI gauge (arc-style SVG).
        2. Horizontal bar chart — ILI per field, sorted descending.
        """
        return [
            _chart_gauge(summary),
            _chart_per_field(summary),
        ]


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _chart_gauge(summary: Dict[str, Any]) -> str:
    """SVG arc gauge showing the global ILI."""
    ili   = summary.get("global_ili", 0.0)
    score = summary.get("utility_score", 1.0 - ili)

    # Color based on score
    color = (
        v.COLOR_SAFE      if score >= 0.8 else
        v.COLOR_THRESHOLD if score >= 0.5 else
        v.COLOR_RISK
    )

    # Arc parameters
    cx, cy, r  = 310, 200, 120
    sw         = 22         # stroke width
    start_deg  = 180
    sweep_deg  = 180
    pct        = min(ili, 1.0)

    def _arc_point(deg: float):
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    def _arc_path(start: float, end: float, col: str) -> str:
        x1, y1 = _arc_point(start)
        x2, y2 = _arc_point(end)
        large  = 1 if abs(end - start) > 180 else 0
        return (
            f'<path d="M {x1:.1f} {y1:.1f} '
            f'A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{col}" stroke-width="{sw}" '
            f'stroke-linecap="round"/>\n'
        )

    end_deg = start_deg + sweep_deg * pct

    svg  = v.svg_open("Information Loss — Global Gauge")
    svg += v.draw_title(
        "Information Loss — Global ILI Gauge",
        f"ILI = {ili:.1%}  ·  Utility score = {score:.1%}",
    )

    # Background arc (gray)
    svg += _arc_path(180, 360, v.COLOR_GRID)
    # Foreground arc (colored by score)
    if pct > 0:
        svg += _arc_path(180, end_deg, color)

    # Center text
    svg += v.text(cx, cy - 10, f"{ili:.1%}", size=32, weight="700",
                  color=color)
    svg += v.text(cx, cy + 20, "Information Loss", size=13,
                  color=v.COLOR_SUBTEXT)
    svg += v.text(cx, cy + 42, f"Utility: {score:.1%}", size=11,
                  color=v.COLOR_SUBTEXT)

    # Scale labels
    svg += v.text(cx - r - 10, cy + 10, "0%",   size=11,
                  color=v.COLOR_SUBTEXT)
    svg += v.text(cx + r + 10, cy + 10, "100%", size=11,
                  color=v.COLOR_SUBTEXT)
    svg += v.text(cx,          cy - r - 14, "50%", size=11,
                  color=v.COLOR_SUBTEXT)

    # Legend
    lx = 80
    svg += v.legend_item(lx,       340, v.COLOR_SAFE,      "Low loss (≤ 20%)")
    svg += v.legend_item(lx + 140, 340, v.COLOR_THRESHOLD, "Moderate (20–50%)")
    svg += v.legend_item(lx + 290, 340, v.COLOR_RISK,      "High loss (> 50%)")

    svg += v.svg_close()
    return svg


def _chart_per_field(summary: Dict[str, Any]) -> str:
    """Horizontal bar chart of ILI per field."""
    per_field = summary.get("per_field", {})
    if not per_field:
        return (v.svg_open("Information Loss per Field")
                + v.text(v.W / 2, v.H / 2, "No data available.")
                + v.svg_close())

    # Sort descending by ILI (highest loss first)
    fields = sorted(per_field.keys(),
                    key=lambda f: per_field[f]["ili"], reverse=True)
    n      = len(fields)

    row_h    = max(22, min(38, int(240 / max(n, 1))))
    chart_h  = v.MT + n * row_h + v.MB + 30
    label_w  = 130
    plot_x   = v.ML + label_w
    plot_w   = v.PW - label_w

    svg = (
        f'<svg viewBox="0 0 {v.W} {chart_h}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Information Loss per Field">\n'
        f'<rect width="{v.W}" height="{chart_h}" '
        f'fill="{v.COLOR_BG}" rx="8"/>\n'
    )
    svg += v.draw_title(
        "Information Loss — ILI per Field",
        "Sorted by information loss descending · lower is better",
    )

    # Grid lines at 0.2 and 0.5
    for threshold, label in [(0.2, "20%"), (0.5, "50%")]:
        tx = plot_x + threshold * plot_w
        svg += v.line(tx, v.MT, tx, v.MT + n * row_h,
                      color=v.COLOR_GRID, width=1, dash="4 3")
        svg += v.text(tx, v.MT - 6, label, size=9, color=v.COLOR_SUBTEXT)

    for i, field in enumerate(fields):
        ili   = per_field[field]["ili"]
        y     = v.MT + i * row_h + 4
        w     = ili * plot_w
        color = (
            v.COLOR_RISK      if ili > 0.5 else
            v.COLOR_THRESHOLD if ili > 0.2 else
            v.COLOR_SAFE
        )

        svg += v.text(plot_x - 6, y + row_h / 2, field,
                      anchor="end", size=10, color=v.COLOR_SUBTEXT)
        if w > 0:
            svg += v.bar(plot_x, y + 2, w, row_h - 6, color, rx=2)
        svg += v.text(plot_x + w + 6, y + row_h / 2,
                      f"{ili:.1%}", anchor="start", size=9,
                      color=v.COLOR_SUBTEXT)

    # X axis at bottom of bars
    axis_y = v.MT + n * row_h
    svg   += v.line(plot_x, axis_y, plot_x + plot_w, axis_y,
                    color=v.COLOR_AXIS, width=1.5)
    svg   += v.text(plot_x, axis_y + 14, "0%",   size=9,
                    anchor="start", color=v.COLOR_SUBTEXT)
    svg   += v.text(plot_x + plot_w, axis_y + 14, "100%", size=9,
                    anchor="end", color=v.COLOR_SUBTEXT)

    svg += v.svg_close()
    return svg


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _build_recommendations(
    global_ili: float,
    score: float,
    high_loss: List[str],
    low_loss: List[str],
    per_field: Dict[str, Dict],
    threshold: float,
) -> List[str]:
    recs = []

    if global_ili <= 0.2:
        recs.append(
            f"Global ILI is {global_ili:.1%} — minimal information loss. "
            "The anonymised dataset retains strong analytical utility."
        )
    elif global_ili <= 0.5:
        recs.append(
            f"Global ILI is {global_ili:.1%} — moderate information loss. "
            "The dataset is still usable but some analyses may be affected. "
            "Validate results on fields with ILI > 20%."
        )
    else:
        recs.append(
            f"Global ILI is {global_ili:.1%} — significant information loss. "
            "The anonymised dataset has limited analytical utility. Consider "
            "using lighter anonymization strategies (noise, generalization) "
            "instead of full redaction or suppression on key fields."
        )

    if high_loss:
        recs.append(
            f"Field(s) with ILI > 50%: {', '.join(high_loss)}. "
            "These fields have lost more than half their original information. "
            "Avoid drawing conclusions from statistical analyses on these fields."
        )

    # Numerical fields where dropped values inflate ILI
    heavy_drop = [
        f for f, s in per_field.items()
        if s.get("n_dropped", 0) > s.get("n_unchanged", 0)
    ]
    if heavy_drop:
        recs.append(
            f"Field(s) {', '.join(heavy_drop)} have more dropped than "
            "retained values. If these fields are needed for analysis, "
            "replace the 'drop' strategy with 'redact' or 'generalize'."
        )

    if not high_loss and score >= threshold:
        recs.append(
            f"All fields meet the acceptable utility threshold "
            f"(score ≥ {threshold:.0%}). The anonymised dataset is "
            "suitable for the intended analytical purpose."
        )

    return recs