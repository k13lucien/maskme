"""
maskme.utility.visual
~~~~~~~~~~~~~~~~~~~~~~
Re-exports all SVG primitives from maskme.analytics.visual.

Utility metrics import from this module so that the dependency path
stays within the utility package. If the primitives ever move, only
this file needs updating — not every metric module.

Usage in a metric module:
    from maskme.utility import visual as v
    svg = v.svg_open("My Chart") + v.bar(...) + v.svg_close()
"""

from maskme.analytics.visual import (  # noqa: F401
    svg_open, svg_close,
    draw_title, text, label_x, label_y,
    bar, line,
    draw_axes, hline, vline,
    legend_item,
    nice_max, bar_layout,
    COLOR_SAFE, COLOR_RISK, COLOR_THRESHOLD,
    COLOR_GRID, COLOR_AXIS, COLOR_TEXT, COLOR_SUBTEXT, COLOR_BG,
    W, H, ML, MR, MT, MB, PW, PH,
)