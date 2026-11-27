"""CPCB PM2.5 air quality categorization for continuous observation values.

Rules for continuous values (my assumption, say so in the docstring):
- value is None, NaN, or negative -> 'no_data'
- value <= 30 -> 'good'
- value <= 60 -> 'satisfactory'
- value <= 90 -> 'moderate'
- value <= 120 -> 'poor'
- value <= 250 -> 'very_poor'
- value > 250 -> 'severe'

NOTE:
The breakpoints above come from user/maintainer notes and are NOT yet
verified against the official CPCB report or gazette notification.
"""

from __future__ import annotations

import math


def pm25_category(value: float | None) -> str:
    """Classify continuous PM2.5 concentration into air quality category.

    Breakpoints from notes (NOT yet verified against official CPCB report):
    - None / NaN / negative (< 0): no_data
    - <= 30: good
    - <= 60: satisfactory
    - <= 90: moderate
    - <= 120: poor
    - <= 250: very_poor
    - > 250: severe
    """
    if value is None:
        return "no_data"

    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return "no_data"

    if math.isnan(val_float) or math.isinf(val_float) or val_float < 0:
        return "no_data"

    if val_float <= 30.0:
        return "good"
    if val_float <= 60.0:
        return "satisfactory"
    if val_float <= 90.0:
        return "moderate"
    if val_float <= 120.0:
        return "poor"
    if val_float <= 250.0:
        return "very_poor"
    return "severe"
