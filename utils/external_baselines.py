"""Literature-reported GFPDO / DPSO anchors from the MACPO paper (F1--F6 only)."""
from __future__ import annotations

# (mean, median, std) per function — transcribed from ref_macpo Table I.
GFPDO_LLSO: dict[str, tuple[float, float, float]] = {
    "F1": (8.46e8, 8.29e8, 8.46e7),
    "F2": (9.43e6, 9.26e6, 4.13e6),
    "F3": (5.86e10, 5.83e10, 4.22e9),
    "F4": (4.53e8, 4.67e8, 6.74e7),
    "F5": (2.11e10, 2.05e10, 2.24e9),
    "F6": (4.00e10, 3.93e10, 4.31e9),
}
DPSO_LLSO: dict[str, tuple[float, float, float]] = {
    "F1": (2.25e10, 2.23e10, 2.66e9),
    "F2": (5.61e10, 1.34e10, 9.39e10),
    "F3": (3.86e10, 3.87e10, 5.62e8),
    "F4": (1.68e10, 1.67e10, 2.33e9),
    "F5": (2.65e10, 2.68e10, 1.87e9),
    "F6": (2.72e10, 2.71e10, 2.87e9),
}
GFPDO_CSO: dict[str, tuple[float, float, float]] = {
    "F1": (2.06e10, 2.06e10, 3.15e9),
    "F2": (2.37e9, 7.07e8, 4.34e9),
    "F3": (1.04e11, 1.03e11, 3.92e9),
    "F4": (8.62e9, 7.43e9, 3.16e9),
    "F5": (5.60e10, 5.57e10, 3.77e9),
    "F6": (5.23e10, 5.22e10, 4.16e9),
}
DPSO_CSO: dict[str, tuple[float, float, float]] = {
    "F1": (3.65e10, 3.72e10, 4.15e9),
    "F2": (2.69e10, 5.56e9, 6.51e10),
    "F3": (3.99e10, 3.97e10, 1.12e9),
    "F4": (1.89e10, 1.82e10, 4.13e9),
    "F5": (4.30e10, 4.31e10, 4.11e9),
    "F6": (4.00e10, 3.27e10, 2.24e10),
}

EXTERNAL_REF_PVALUE = "---"
