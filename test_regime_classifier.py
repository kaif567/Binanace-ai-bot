"""
Unit tests for indicators/regime.py

Run:
    pytest test_regime_classifier.py -v

All 7 tests must pass. They do NOT call Binance API or read any JSON files.
They only test the pure classify_regime() function in isolation.
"""

import pandas as pd
import numpy as np
import pytest

from indicators.regime import classify_regime


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Thresholds used in all tests — chosen to be unambiguous for testing.
# The sweep will find the real production values; these are just for isolation.
TEST_ADX_TRENDING = 22.0
TEST_ADX_RANGING = 18.0
TEST_ATR_LOOKBACK = 24       # candles back for ATR comparison
TEST_ATR_CHANGE_THRESH = 0.30  # 30% ATR surge → HIGH_VOLATILITY


def _make_df(adx_values, atr_values):
    """Build a minimal DataFrame with adx and atr columns."""
    assert len(adx_values) == len(atr_values), "lengths must match"
    return pd.DataFrame({"adx": adx_values, "atr": atr_values})


def _flat_df(n_rows, adx, atr):
    """Build a flat DataFrame with constant adx and atr."""
    return _make_df([adx] * n_rows, [atr] * n_rows)


def _call(df):
    """Call classify_regime with test thresholds."""
    return classify_regime(
        df,
        adx_trending_thresh=TEST_ADX_TRENDING,
        adx_ranging_thresh=TEST_ADX_RANGING,
        atr_lookback=TEST_ATR_LOOKBACK,
        atr_change_thresh=TEST_ATR_CHANGE_THRESH,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — TRENDING detection
# ─────────────────────────────────────────────────────────────────────────────

def test_trending_detection():
    """ADX clearly above trending threshold → TRENDING."""
    df = _flat_df(n_rows=50, adx=30.0, atr=500.0)
    result = _call(df)
    assert result == "TRENDING", (
        f"Expected TRENDING for ADX=30 (thresh={TEST_ADX_TRENDING}), got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — RANGING detection
# ─────────────────────────────────────────────────────────────────────────────

def test_ranging_detection():
    """ADX clearly below ranging threshold → RANGING."""
    df = _flat_df(n_rows=50, adx=12.0, atr=500.0)
    result = _call(df)
    assert result == "RANGING", (
        f"Expected RANGING for ADX=12 (thresh={TEST_ADX_RANGING}), got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — HIGH_VOLATILITY detection
# ─────────────────────────────────────────────────────────────────────────────

def test_high_volatility_detection():
    """
    ATR surge > 30% over TEST_ATR_LOOKBACK candles → HIGH_VOLATILITY.
    The ADX is set above trending threshold to confirm HIGH_VOL takes priority.
    """
    n_rows = TEST_ATR_LOOKBACK + 10
    atr_values = [500.0] * n_rows
    # Make the last row have a 60% ATR spike
    atr_values[-1] = 500.0 * 1.60

    adx_values = [30.0] * n_rows  # trending ADX — HIGH_VOL should still win

    df = _make_df(adx_values, atr_values)
    result = _call(df)
    assert result == "HIGH_VOLATILITY", (
        f"Expected HIGH_VOLATILITY for 60% ATR surge, got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Graceful NaN handling
# ─────────────────────────────────────────────────────────────────────────────

def test_nan_adx_returns_unknown():
    """NaN ADX → UNKNOWN (never crashes, never silently blocks)."""
    df = _flat_df(n_rows=50, adx=float("nan"), atr=500.0)
    result = _call(df)
    assert result == "UNKNOWN", (
        f"Expected UNKNOWN for NaN ADX, got {result}"
    )


def test_missing_columns_returns_unknown():
    """DataFrame without adx/atr columns → UNKNOWN."""
    df = pd.DataFrame({"close": [50000.0] * 10})
    result = _call(df)
    assert result == "UNKNOWN"


def test_empty_df_returns_unknown():
    """Empty DataFrame → UNKNOWN (no crash)."""
    df = pd.DataFrame()
    result = _call(df)
    assert result == "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Threshold boundary (strict inequality)
# ─────────────────────────────────────────────────────────────────────────────

def test_adx_exactly_on_trending_threshold_is_ranging():
    """
    ADX == adx_trending_thresh (not strictly above) → RANGING (grey zone).
    We use strict '>'; exactly on threshold is treated as ambiguous/ranging.
    """
    df = _flat_df(n_rows=50, adx=TEST_ADX_TRENDING, atr=500.0)
    result = _call(df)
    assert result == "RANGING", (
        f"ADX exactly equal to trending threshold ({TEST_ADX_TRENDING}) "
        f"should be RANGING (grey zone), got {result}"
    )


def test_adx_one_tick_above_trending_threshold_is_trending():
    """ADX just barely above trending threshold → TRENDING."""
    df = _flat_df(n_rows=50, adx=TEST_ADX_TRENDING + 0.01, atr=500.0)
    result = _call(df)
    assert result == "TRENDING", (
        f"ADX just above trending threshold should be TRENDING, got {result}"
    )


def test_adx_exactly_on_ranging_threshold_is_ranging():
    """ADX == adx_ranging_thresh (not strictly below) → grey zone → RANGING."""
    df = _flat_df(n_rows=50, adx=TEST_ADX_RANGING, atr=500.0)
    result = _call(df)
    assert result == "RANGING"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — ATR surge check needs sufficient history
# ─────────────────────────────────────────────────────────────────────────────

def test_insufficient_history_for_atr_skips_vol_check():
    """
    If df has fewer rows than atr_lookback + 1, the ATR surge check is
    skipped. A strong ADX should still produce TRENDING.
    """
    # Only 10 rows, but lookback is 24 → not enough for ATR comparison
    n_rows = 10
    df = _flat_df(n_rows=n_rows, adx=30.0, atr=500.0)
    result = _call(df)
    # Should NOT be UNKNOWN or HIGH_VOLATILITY; ADX path should fire
    assert result == "TRENDING", (
        f"With insufficient ATR history, ADX={30.0} should still give TRENDING, got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — ATR surge exactly on threshold is NOT high-volatility
# ─────────────────────────────────────────────────────────────────────────────

def test_atr_surge_exactly_on_threshold_not_high_vol():
    """
    ATR surge == atr_change_thresh (not strictly above) → NOT HIGH_VOLATILITY.
    Strict '>' required so threshold itself passes through.
    """
    n_rows = TEST_ATR_LOOKBACK + 10
    atr_base = 500.0
    # Exactly 30% surge
    atr_values = [atr_base] * n_rows
    atr_values[-1] = atr_base * (1.0 + TEST_ATR_CHANGE_THRESH)

    adx_values = [30.0] * n_rows  # trending
    df = _make_df(adx_values, atr_values)
    result = _call(df)
    # Exactly on threshold → NOT high_volatility; ADX path → TRENDING
    assert result == "TRENDING", (
        f"ATR surge exactly on threshold should not trigger HIGH_VOLATILITY, got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test — None df
# ─────────────────────────────────────────────────────────────────────────────

def test_none_df_returns_unknown():
    """None DataFrame → UNKNOWN (no crash)."""
    result = classify_regime(
        None,
        adx_trending_thresh=22.0,
        adx_ranging_thresh=18.0,
        atr_lookback=24,
        atr_change_thresh=0.30,
    )
    assert result == "UNKNOWN"

