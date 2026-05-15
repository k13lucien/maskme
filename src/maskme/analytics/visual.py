"""
maskme.analytics.visual
~~~~~~~~~~~~~~~~~~~~~~~~
Pure SVG primitives for analytics chart generation.

This module provides low-level building blocks only — rectangles, lines,
text, axes, titles, and legends. Each analytic module is responsible for
assembling these primitives into its own charts.

This design means visual.py never needs to change when a new analytic is
added. Chart logic lives alongside compute() in each analytic module.

Public primitives:
    svg_open(aria_label)          → str
    svg_close()                   → str
    draw_title(title, subtitle)   → str
    draw_axes(y_max, ...)         → str
    bar(x, y, w, h, fill)        → str
    hline(y_val, y_max, label)   → str
    vline(x_pos, label)          → str
    label_x(x, y, text)          → str
    label_y(x, y, text)          → str
    legend_item(x, y, color, label) → str
    nice_max(value)               → float

Design tokens (importable for use in analytic modules):
    COLOR_SAFE, COLOR_RISK, COLOR_THRESHOLD, COLOR_SUBTEXT
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Design tokens — import these in analytic modules for visual consistency
# ---------------------------------------------------------------------------

COLOR_SAFE      = "#4A7A2C"   # olive    — satisfies threshold
COLOR_RISK      = "#C44536"   # warm red — violates threshold
COLOR_THRESHOLD = "#C4942A"   # amber    — threshold marker
COLOR_GRID      = "#E8E4C8"   # cream-tinted grid
COLOR_AXIS      = "#8B8B7A"   # muted olive-gray
COLOR_TEXT      = "#2E2E2E"   # near-black
COLOR_SUBTEXT   = "#8B8B7A"
COLOR_BG        = "#FFFFFF"

_FONT = "font-family=\"-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif\""

# Canvas dimensions (viewBox units) — importable for layout calculations
W, H      = 620, 360
ML, MR    = 64, 24      # margin left / right
MT, MB    = 48, 64      # margin top / bottom
PW        = W - ML - MR  # plot width
PH        = H - MT - MB  # plot height


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

def svg_open(aria_label: str) -> str:
    """Open an SVG canvas with a white rounded background."""
    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="{aria_label}">\n'
        f'<rect width="{W}" height="{H}" fill="{COLOR_BG}" rx="8"/>\n'
    )


def svg_close() -> str:
    """Close the SVG element."""
    return "</svg>"


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

def draw_title(title: str, subtitle: str = "") -> str:
    """Render a chart title and optional subtitle."""
    svg  = text(W / 2, 24, title, size=13, weight="600")
    if subtitle:
        svg += text(W / 2, 40, subtitle, size=10, color=COLOR_SUBTEXT)
    return svg


def text(x: float, y: float, content: str, **attrs) -> str:
    """Render a text element."""
    size   = attrs.get("size", 12)
    anchor = attrs.get("anchor", "middle")
    color  = attrs.get("color", COLOR_TEXT)
    weight = attrs.get("weight", "normal")
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" {_FONT} font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" fill="{color}">'
        f'{content}</text>\n'
    )


def label_x(x: float, y: float, content: str) -> str:
    """Render an X-axis tick label."""
    return text(x, y, content, size=10, color=COLOR_SUBTEXT)


def label_y(x: float, y: float, content: str) -> str:
    """Render a Y-axis tick label."""
    return text(x, y, content, anchor="end", size=10, color=COLOR_SUBTEXT)


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

def bar(x: float, y: float, w: float, h: float,
        fill: str, rx: int = 3) -> str:
    """Render a filled rectangle (bar)."""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" '
        f'width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" rx="{rx}"/>\n'
    )


def line(x1: float, y1: float, x2: float, y2: float,
         color: str = COLOR_GRID, width: float = 1,
         dash: str = "") -> str:
    """Render a line segment."""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
        f'x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}"{dash_attr}/>\n'
    )


# ---------------------------------------------------------------------------
# Axis helpers
# ---------------------------------------------------------------------------

def draw_axes(y_max: float, y_label: str, x_label: str,
              n_y_ticks: int = 5) -> str:
    """Draw grid lines, Y-axis ticks, and axis labels."""
    svg  = ""
    step = y_max / n_y_ticks

    for i in range(n_y_ticks + 1):
        val   = step * i
        y_pos = MT + PH - (val / y_max) * PH
        svg  += line(ML, y_pos, ML + PW, y_pos, color=COLOR_GRID)
        fmt   = (f"{val:.2f}" if isinstance(val, float) and val != int(val)
                 else str(int(val)))
        svg  += label_y(ML - 8, y_pos + 4, fmt)

    # Axis borders
    svg += line(ML, MT, ML, MT + PH, color=COLOR_AXIS, width=1.5)
    svg += line(ML, MT + PH, ML + PW, MT + PH, color=COLOR_AXIS, width=1.5)

    # Axis labels
    svg += text(W / 2, H - 6, x_label, size=11, color=COLOR_SUBTEXT)
    svg += (
        f'<text x="14" y="{MT + PH / 2:.1f}" {_FONT} font-size="11" '
        f'fill="{COLOR_SUBTEXT}" text-anchor="middle" '
        f'transform="rotate(-90, 14, {MT + PH / 2:.1f})">'
        f'{y_label}</text>\n'
    )
    return svg


def hline(y_val: float, y_max: float, label: str = "") -> str:
    """Draw a dashed horizontal threshold line."""
    y_pos = MT + PH - (y_val / y_max) * PH
    svg   = line(ML, y_pos, ML + PW, y_pos,
                 color=COLOR_THRESHOLD, width=2, dash="6 3")
    if label:
        svg += text(ML + PW - 4, y_pos - 6, label,
                    anchor="end", size=10,
                    color=COLOR_THRESHOLD, weight="600")
    return svg


def vline(x_pos: float, label: str = "") -> str:
    """Draw a dashed vertical threshold line."""
    svg = line(x_pos, MT, x_pos, MT + PH,
               color=COLOR_THRESHOLD, width=2, dash="6 3")
    if label:
        svg += text(x_pos + 4, MT + 14, label,
                    anchor="start", size=10,
                    color=COLOR_THRESHOLD, weight="600")
    return svg


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------

def legend_item(x: float, y: float, color: str, label: str) -> str:
    """Render a single colour-coded legend entry."""
    return (
        bar(x, y - 8, 14, 14, color, rx=2)
        + text(x + 20, y + 3, label, anchor="start",
               size=11, color=COLOR_SUBTEXT)
    )


# ---------------------------------------------------------------------------
# Layout utilities
# ---------------------------------------------------------------------------

def nice_max(value: float) -> float:
    """Round up to a 'nice' axis maximum."""
    if value == 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(value))
    return math.ceil(value / magnitude) * magnitude


def bar_layout(n_bars: int, max_bar_w: float = 60) -> tuple[float, float]:
    """
    Compute bar width and gap for a given number of bars.

    Returns:
        (bar_width, bar_gap)
    """
    bar_gap = PW / n_bars
    bar_w   = min(bar_gap * 0.70, max_bar_w)
    return bar_w, bar_gap