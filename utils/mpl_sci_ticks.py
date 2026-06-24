"""
Matplotlib tick helpers: ASCII scientific notation and log-scale “ruler” minors.

Used by RL metric plots and similar figures; keep formatting consistent repo-wide.
"""
from __future__ import annotations

import numpy as np
import matplotlib.ticker as mticker


def fmt_tick_sci_ascii(v: float, _pos: int | None = None) -> str:
    """Single-tick scientific notation (ASCII e), no mathtext superscripts."""
    if not np.isfinite(v):
        return ""
    if v == 0.0:
        return "0"
    return f"{v:.2e}"


def set_xaxis_eval_sci(ax) -> None:
    """Horizontal axis: cumulative evaluations / FES in scientific notation."""
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_tick_sci_ascii))


def set_xaxis_eval_sci_sparse(ax, *, max_ticks: int = 5) -> None:
    """
    FES / evaluations on x: scientific notation with a bounded number of major ticks.

    Use with ``sharex=True`` grids so labels stay readable (avoid tick overlap).
    Minor ticks between majors (``AutoMinorLocator``) pair with shorter minor tick length
    from :func:`style_axes_reference`.
    """
    ax.xaxis.set_major_locator(
        mticker.MaxNLocator(nbins=max_ticks, prune="both", min_n_ticks=3)
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_tick_sci_ascii))
    ax.xaxis.set_minor_locator(mticker.AutoMinorLocator(4))


def set_yaxis_sci_linear(ax) -> None:
    """Linear y-axis with scientific tick labels."""
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_tick_sci_ascii))


def set_yaxis_log_ruler(ax) -> None:
    """
    Logarithmic y with decade majors and minor ticks (log “ruler”).

    Tick labels use ASCII scientific values at each major (e.g. 1.00e+02).
    """
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_tick_sci_ascii))
    ax.yaxis.set_major_locator(mticker.LogLocator(base=10))
    ax.yaxis.set_minor_locator(mticker.LogLocator(base=10, subs=np.arange(2, 10)))
    ax.minorticks_on()


def style_axes_reference(ax) -> None:
    """
    Inward ticks + light grid (major), similar to paper line-plot style.

    Major tick marks are visibly longer than minor ticks (clearer “ruler” read).
    """
    ax.tick_params(
        axis="both",
        which="major",
        direction="in",
        length=5.5,
        width=0.9,
    )
    ax.tick_params(
        axis="both",
        which="minor",
        direction="in",
        length=2.0,
        width=0.55,
    )
    ax.grid(True, which="major", color="lightgray", linestyle="-", alpha=0.9)


def set_numeric_tick_font_dejavu(ax) -> None:
    """Avoid missing glyphs on numeric ticks when the body font is CJK."""
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontfamily("DejaVu Sans")
