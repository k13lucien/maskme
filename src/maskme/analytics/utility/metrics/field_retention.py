"""
maskme.analytics.utility.metrics.field_retention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Field Retention metric.

Measures what fraction of the data survives anonymization at the field
level, distinguishing three value states:

    unchanged — identical to the original value
    modified  — present in both but the value changed
    dropped   — present in original, absent in anonymised (via drop strategy)

Global score: weighted average retention rate across all fields.
    score = 1.0 → every value is identical to the original (no anonymization)
    score = 0.0 → every value was dropped or modified beyond recognition

Chart: horizontal stacked bar chart — one bar per field showing the
       proportion of unchanged / modified / dropped values.
"""

from __future__ import annotations

from typing import Any, Dict, List

from maskme.analytics import visual as v
from maskme.analytics.utility.metrics.base import Metric, UtilityResult
from maskme.analytics.utility.metrics._utils import (
    all_fields,
    paired_values,
    validate_alignment,
    value_changed,
    value_dropped,
)


class FieldRetention:
    """
    Measures value-level retention across all fields after anonymization.

    For each field, classifies every (original, anonymised) value pair as:
      - unchanged : values are identical
      - modified  : both present but values differ
      - dropped   : present in original, absent in anonymised
    """

    name = "Field Retention"

    def compute(
        self,
        original: List[Dict[str, Any]],
        anonymised: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> UtilityResult:
        """
        Evaluate field-level retention across original and anonymised datasets.

        Args:
            original:   The original dataset before anonymization.
            anonymised: The anonymised dataset produced by MaskMe.
            **kwargs:   Ignored (forwarded by the utility runner).

        Returns:
            UtilityResult with per-field retention breakdown and global score.

        Raises:
            ValueError: If datasets have different lengths or are empty.
        """
        if not original:
            raise ValueError("Cannot compute field retention on an empty dataset.")

        validate_alignment(original, anonymised)

        fields     = all_fields(original)
        n_records  = len(original)
        per_field  = {}

        for field in fields:
            pairs     = paired_values(original, anonymised, field)
            n_dropped  = sum(1 for o, a in pairs if value_dropped(o, a))
            n_modified = sum(
                1 for o, a in pairs
                if not value_dropped(o, a) and value_changed(o, a)
            )
            n_unchanged = n_records - n_dropped - n_modified

            retention  = round(n_unchanged / n_records, 4)
            per_field[field] = {
                "unchanged":      n_unchanged,
                "modified":       n_modified,
                "dropped":        n_dropped,
                "retention_rate": retention,
                "pct_unchanged":  round(100 * n_unchanged  / n_records, 1),
                "pct_modified":   round(100 * n_modified   / n_records, 1),
                "pct_dropped":    round(100 * n_dropped    / n_records, 1),
            }

        # Global metrics
        fully_dropped    = [f for f, s in per_field.items() if s["dropped"] == n_records]
        fully_unchanged  = [f for f, s in per_field.items() if s["unchanged"] == n_records]
        global_retention = round(
            sum(s["retention_rate"] for s in per_field.values()) / len(fields), 4
        )
        score   = global_retention
        passed  = score >= kwargs.get("threshold", 0.5)

        summary = {
            "global_retention_rate": global_retention,
            "total_fields":          len(fields),
            "fully_dropped_fields":  len(fully_dropped),
            "fully_unchanged_fields": len(fully_unchanged),
            "total_records":         n_records,
            "fields":                list(per_field.keys()),
            "per_field":             per_field,
        }

        details = sorted(
            [
                {
                    "field":          field,
                    "retention_rate": stats["retention_rate"],
                    "pct_unchanged":  stats["pct_unchanged"],
                    "pct_modified":   stats["pct_modified"],
                    "pct_dropped":    stats["pct_dropped"],
                    "status": (
                        "dropped"   if stats["dropped"]   == n_records else
                        "unchanged" if stats["unchanged"] == n_records else
                        "partial"
                    ),
                }
                for field, stats in per_field.items()
            ],
            key=lambda d: d["retention_rate"],
        )

        recommendations = _build_recommendations(
            global_retention, fully_dropped, fully_unchanged,
            per_field, n_records,
        )

        return UtilityResult(
            name=self.name,
            score=score,
            passed=passed,
            summary=summary,
            details=details,
            recommendations=recommendations,
            threshold=kwargs.get("threshold", 0.5),
            metadata={
                "total_fields":  len(fields),
                "total_records": n_records,
            },
        )

    def chart(self, summary: Dict[str, Any]) -> List[str]:
        """
        Horizontal stacked bar chart — one bar per field.

        Each bar shows the proportion of unchanged (green) / modified
        (amber) / dropped (red) values for that field.
        """
        per_field: Dict[str, Dict] = summary.get("per_field", {})
        if not per_field:
            return [v.svg_open("Field Retention")
                    + v.text(v.W / 2, v.H / 2, "No data available.")
                    + v.svg_close()]

        fields    = list(per_field.keys())
        n         = len(fields)

        # Dynamic canvas height based on number of fields
        row_h     = max(22, min(40, int(260 / max(n, 1))))
        chart_h   = v.MT + n * row_h + v.MB + 20
        bar_area  = v.PW
        label_w   = 120

        svg = (
            f'<svg viewBox="0 0 {v.W} {chart_h}" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Field Retention">\n'
            f'<rect width="{v.W}" height="{chart_h}" '
            f'fill="{v.COLOR_BG}" rx="8"/>\n'
        )
        svg += v.draw_title(
            "Field Retention — Value State per Field",
            f"Global retention rate: "
            f"{round(summary.get('global_retention_rate', 0) * 100, 1)}%  ·  "
            f"{summary.get('fully_dropped_fields', 0)} field(s) fully dropped",
        )

        plot_x = v.ML + label_w
        plot_w = bar_area - label_w

        for i, field in enumerate(fields):
            stats = per_field[field]
            y     = v.MT + i * row_h + 4

            # Field label
            svg += v.text(
                plot_x - 6, y + row_h / 2, field,
                anchor="end", size=10, color=v.COLOR_SUBTEXT,
            )

            # Stacked bar segments
            x_cursor = plot_x
            for pct, color in [
                (stats["pct_unchanged"], v.COLOR_SAFE),
                (stats["pct_modified"],  v.COLOR_THRESHOLD),
                (stats["pct_dropped"],   v.COLOR_RISK),
            ]:
                w = (pct / 100) * plot_w
                if w > 0:
                    svg += v.bar(x_cursor, y + 2, w, row_h - 6, color, rx=2)
                    if w > 24:
                        svg += v.text(
                            x_cursor + w / 2, y + row_h / 2 + 1,
                            f"{pct:.0f}%",
                            size=9, color="#fff",
                        )
                    x_cursor += w

            # Retention rate label at right
            svg += v.text(
                plot_x + plot_w + 6, y + row_h / 2,
                f"{stats['retention_rate'] * 100:.1f}%",
                anchor="start", size=9, color=v.COLOR_SUBTEXT,
            )

        # Legend at bottom
        legend_y = v.MT + n * row_h + 14
        svg += v.legend_item(plot_x,           legend_y, v.COLOR_SAFE,      "Unchanged")
        svg += v.legend_item(plot_x + 100,     legend_y, v.COLOR_THRESHOLD, "Modified")
        svg += v.legend_item(plot_x + 190,     legend_y, v.COLOR_RISK,      "Dropped")

        svg += v.svg_close()
        return [svg]


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _build_recommendations(
    global_retention: float,
    fully_dropped: List[str],
    fully_unchanged: List[str],
    per_field: Dict[str, Dict],
    n_records: int,
) -> List[str]:
    recs = []

    pct = round(global_retention * 100, 1)

    if global_retention >= 0.9:
        recs.append(
            f"Global retention rate is {pct}% — the anonymised dataset "
            "preserves the vast majority of its original values."
        )
    elif global_retention >= 0.6:
        recs.append(
            f"Global retention rate is {pct}%. A significant portion of "
            "values have been modified or dropped. Validate that downstream "
            "use cases still function correctly."
        )
    else:
        recs.append(
            f"Global retention rate is only {pct}%. The anonymised dataset "
            "has lost substantial information — consider relaxing anonymization "
            "rules for fields not strictly required to be masked."
        )

    if fully_dropped:
        recs.append(
            f"The following field(s) were entirely removed by the drop "
            f"strategy and are no longer available: "
            f"{', '.join(fully_dropped)}. "
            "Confirm these fields are not needed for analysis."
        )

    # Warn on highly modified fields (> 50% values changed)
    high_mod = [
        f for f, s in per_field.items()
        if s["pct_modified"] > 50 and s["dropped"] < n_records
    ]
    if high_mod:
        recs.append(
            f"Field(s) {', '.join(high_mod)} have more than 50% of their "
            "values modified. Statistical analyses on these fields may yield "
            "unreliable results."
        )

    if fully_unchanged:
        recs.append(
            f"Field(s) {', '.join(fully_unchanged)} were left entirely "
            "unchanged. Verify these fields do not constitute quasi-identifiers "
            "that could enable re-identification."
        )

    return recs