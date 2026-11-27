"""Tests for features/categories.py."""

from __future__ import annotations

import math

from features.categories import pm25_category


def test_pm25_category_breakpoints() -> None:
    """Test PM2.5 category assignments at and around all breakpoints.

    Breakpoints:
    <= 30: good
    <= 60: satisfactory
    <= 90: moderate
    <= 120: poor
    <= 250: very_poor
    > 250: severe
    """
    assert pm25_category(0.0) == "good"
    assert pm25_category(15.0) == "good"
    assert pm25_category(30.0) == "good"

    assert pm25_category(30.1) == "satisfactory"
    assert pm25_category(45.0) == "satisfactory"
    assert pm25_category(60.0) == "satisfactory"

    assert pm25_category(60.1) == "moderate"
    assert pm25_category(75.0) == "moderate"
    assert pm25_category(90.0) == "moderate"

    assert pm25_category(90.1) == "poor"
    assert pm25_category(105.0) == "poor"
    assert pm25_category(120.0) == "poor"

    assert pm25_category(121.0) == "very_poor"
    assert pm25_category(200.0) == "very_poor"
    assert pm25_category(250.0) == "very_poor"

    assert pm25_category(250.1) == "severe"
    assert pm25_category(300.0) == "severe"
    assert pm25_category(500.0) == "severe"


def test_pm25_category_edge_cases() -> None:
    """Test edge cases: None, NaN, inf, negative values, and non-numeric inputs."""
    assert pm25_category(None) == "no_data"
    assert pm25_category(float("nan")) == "no_data"
    assert pm25_category(math.nan) == "no_data"
    assert pm25_category(float("inf")) == "no_data"
    assert pm25_category(float("-inf")) == "no_data"

    # Negative values
    assert pm25_category(-5.0) == "no_data"
    assert pm25_category(-0.01) == "no_data"

    # Non-numeric string / invalid types
    assert pm25_category("invalid") == "no_data"  # type: ignore[arg-type]
