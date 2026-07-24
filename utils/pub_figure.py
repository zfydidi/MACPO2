"""Publication figure helpers (Nature/IEEE-oriented, Python/matplotlib only).

Reused by gated_* and related plotting scripts so panel labels, fonts, and
export defaults stay consistent. Aligns with nature-figure backend quick-start
(sans-serif, editable PDF text, no top/right spines, lowercase panel letters).
"""
from __future__ import annotations

import matplotlib as mpl


def apply_pub_style(*, font_size: float = 7.0) -> None:
    """Apply a conservative journal figure style (Nature-figure Python defaults)."""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": font_size,
        "axes.labelsize": font_size,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
        "legend.fontsize": font_size,
        "axes.titlesize": font_size + 1,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "axes.unicode_minus": False,
    })


def panel_label(ax, letter: str, *, x: float = -0.12, y: float = 1.08) -> None:
    """Bold lowercase panel letter near the top-left (Nature figure guide)."""
    ax.text(
        x, y, letter.lower(), transform=ax.transAxes,
        fontsize=8, fontweight="bold", va="bottom", ha="left",
        fontfamily="sans-serif",
    )
