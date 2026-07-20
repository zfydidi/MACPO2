"""
Matplotlib CJK font setup — single source of truth for plotting scripts.
Fails loudly if no suitable CJK-capable font is found.
"""
from __future__ import annotations

import matplotlib
from matplotlib import font_manager

_CANDIDATES = [
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "STHeiti",
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
]


def setup_cjk_font() -> str:
    """
    Configure Matplotlib to use a CJK-capable sans-serif font.
    Sets axes.unicode_minus = False for correct minus rendering.
    Returns the chosen font family name.
    Raises RuntimeError if none of the candidate fonts are available.
    """
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CANDIDATES:
        if name in available:
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            # 让 mathtext（$...$）也回退到可用字体，避免希腊字母/负号缺字形
            matplotlib.rcParams["mathtext.fontset"] = "dejavusans"
            return name
    raise RuntimeError(
        "No CJK-capable font found in this environment. Install a Noto/SimHei/PingFang font "
        f"or extend utils/mpl_font._CANDIDATES. Tried: {_CANDIDATES}"
    )
