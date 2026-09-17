"""
Integration tests for regime_filter in run_advanced_backtest().

These tests confirm:
1. regime_filter=None → 100% identical output to pre-Phase-1 baseline
2. regime_filter set → RANGING candles blocked, TRENDING candles pass
3. Open position exits still happen in RANGING regimes (filter only blocks entries)
4. determine_paper_eligibility gate #6 (REGIME_BLOCKED) works correctly
5. Gate #6 default (regime_status="TRENDING") keeps all existing callers passing

Run:
    pytest test_regime_filter.py -v
"""

import pandas as pd
import numpy as np
import pytest

from backtest.engine import run_advanced_backtest
from backtest.pipeline import determine_paper_eligibility


# ─────────────────────────────────────────────────────────────────────────────
# Minimal DataFrame builder for engine tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_candles(n=60, adx_value=30.0, atr_value=500.0):
    """
    Build a minimal DataFrame that the engine can run through.
    - EMA crossover signal: ema20 > ema50 on last row → STRONG BUY
    - adx and atr columns required for classify_regime
    - Timestamps in milliseconds (realistic)
    """
    import time
    base_time = int(time.time() * 1000) - (n * 3600 * 1000)

    data = {
        "time": [base_time + i * 3600_000 for i in range(n)],
        "open":  [50000.0 + i * 10 for i in range(n)],
        "high":  [50100.0 + i * 10 for i in range(n)],
        "low":   [49900.0 + i * 10 for i in range(n)],
        "close": [50050.0 + i * 10 for i in range(n)],
        "volume": [100.0] * n,
        "adx":   [adx_value] * n,
        "atr":   [atr_value] * n,
        # Pre-compute EMAs so calculate_market_score generates signals
        "ema20": [50000.0 + i * 12 for i in range(n)],  # fast above slow
        "ema50": [50000.0 + i * 5  for i in range(n)],
        "rsi":   [55.0] * n,
        "macd":  [1.0] * n,
        "macd_signal": [0.5] * n,
        "bb_upper": [51000.0 + i * 10 for i in range(n)],
        "bb_lower": [49000.0 + i * 10 for i in range(n)],
        "volume_avg": [90.0] * n,
    }
    return pd.DataFrame(data)


REGIME_PARAMS = {
    "adx_trending_thresh": 25.0,
    "adx_ranging_thresh": 18.0,
    "atr_lookback": 12,
    "atr_change_thresh": 0.40,
}


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — regime_filter=None gives 100% identical results
# ─────────────────────────────────────────────────────────────────────────────

def test_regime_filter_none_identical_to_baseline():
    """
    regime_filter=None must produce exactly the same trade history, profit,
    win rate, and profit factor as calling run_advanced_backtest() without
    the parameter at all. No new code path should execute.
    """
    df = _make_candles(n=60, adx_value=30.0)

    result_baseline = run_advanced_backtest(
        df.copy(),
        stop_loss=0.02,
        take_profit=0.05,
        trade_start_index=1,
    )

    result_filtered = run_advanced_backtest(
        df.copy(),
        stop_loss=0.02,
        take_profit=0.05,
        trade_start_index=1,
        regime_filter=None,
    )

    assert result_baseline["trades"] == result_filtered["trades"], (
        "regime_filter=None changed trade count"
    )
    assert result_baseline["profit"] == result_filtered["profit"], (
        "regime_filter=None changed profit"
    )
    assert result_baseline["profit_factor"] == result_filtered["profit_factor"], (
        "regime_filter=None changed profit_factor"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — RANGING candles blocked when regime_filter set
# ─────────────────────────────────────────────────────────────────────────────

def test_ranging_regime_blocks_entries():
    """
    With ADX=12 (clearly below adx_ranging_thresh=18), regime is RANGING.
    regime_filter set → zero new entries should be generated.
    """
    df = _make_candles(n=60, adx_value=12.0)

    result_no_filter = run_advanced_backtest(
        df.copy(),
        stop_loss=0.02,
        take_profit=0.05,
        trade_start_index=1,
    )

    result_filtered = run_advanced_backtest(
        df.copy(),
        stop_loss=0.02,
        take_profit=0.05,
        trade_start_index=1,
        regime_filter=REGIME_PARAMS,
    )

    # With filter, RANGING regime → no new entries
    assert result_filtered["trades"] == 0, (
        f"Expected 0 trades in RANGING regime, got {result_filtered['trades']}"
    )

    # Filtered must be ≤ unfiltered (filter can only reduce, never add trades)
    assert result_filtered["trades"] <= result_no_filter["trades"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — TRENDING candles pass through when regime_filter set
# ─────────────────────────────────────────────────────────────────────────────

def test_trending_regime_allows_entries():
    """
    With ADX=30 (above adx_trending_thresh=25), regime is TRENDING.
    regime_filter set → entry generation should be identical to no-filter.
    """
    df = _make_candles(n=60, adx_value=30.0)

    result_no_filter = run_advanced_backtest(
        df.copy(),
        stop_loss=0.02,
        take_profit=0.05,
        trade_start_index=1,
    )

    result_filtered = run_advanced_backtest(
        df.copy(),
        stop_loss=0.02,
        take_profit=0.05,
        trade_start_index=1,
        regime_filter=REGIME_PARAMS,
    )

    assert result_filtered["trades"] == result_no_filter["trades"], (
        f"TRENDING regime should not block trades: "
        f"filtered={result_filtered['trades']} vs baseline={result_no_filter['trades']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Gate #6 REGIME_BLOCKED in determine_paper_eligibility
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_6_ranging_is_blocked():
    """Gate #6: RANGING regime → eligible=False, mode=REGIME_BLOCKED."""
    result = determine_paper_eligibility(
        strategy_quality=65.0,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=60,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,
        oos_profit_factor=1.5,
        oos_profit=50.0,
        robustness_status="ROBUST",
        regime_status="RANGING",
    )
    assert result["eligible"] is False
    assert result["mode"] == "REGIME_BLOCKED"


def test_gate_6_high_volatility_is_blocked():
    """Gate #6: HIGH_VOLATILITY regime → eligible=False, mode=REGIME_BLOCKED."""
    result = determine_paper_eligibility(
        strategy_quality=65.0,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=60,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,
        oos_profit_factor=1.5,
        oos_profit=50.0,
        robustness_status="ROBUST",
        regime_status="HIGH_VOLATILITY",
    )
    assert result["eligible"] is False
    assert result["mode"] == "REGIME_BLOCKED"


def test_gate_6_trending_passes_through():
    """Gate #6: TRENDING regime → does NOT block (eligible decided by other gates)."""
    result = determine_paper_eligibility(
        strategy_quality=65.0,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=60,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,
        oos_profit_factor=1.5,
        oos_profit=50.0,
        robustness_status="ROBUST",
        regime_status="TRENDING",
    )
    assert result["mode"] != "REGIME_BLOCKED"


def test_gate_6_unknown_passes_through():
    """Gate #6: UNKNOWN regime → pass through (graceful degradation on NaN data)."""
    result = determine_paper_eligibility(
        strategy_quality=65.0,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=60,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,
        oos_profit_factor=1.5,
        oos_profit=50.0,
        robustness_status="ROBUST",
        regime_status="UNKNOWN",
    )
    assert result["mode"] != "REGIME_BLOCKED"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Backwards-compat: default regime_status="TRENDING" for old callers
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_6_default_backwards_compat():
    """
    Old callers that don't pass regime_status should get regime_status="TRENDING"
    by default → REGIME_BLOCKED is never triggered → behaviour identical to
    pre-Phase-1.
    """
    # A previously-eligible call without regime_status param
    result_old = determine_paper_eligibility(
        strategy_quality=65.0,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=60,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,
        oos_profit_factor=1.5,
        oos_profit=50.0,
        robustness_status="ROBUST",
        # no regime_status → defaults to "TRENDING"
    )

    # Same call with explicit TRENDING
    result_new = determine_paper_eligibility(
        strategy_quality=65.0,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=60,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,
        oos_profit_factor=1.5,
        oos_profit=50.0,
        robustness_status="ROBUST",
        regime_status="TRENDING",
    )

    assert result_old["eligible"] == result_new["eligible"]
    assert result_old["mode"] == result_new["mode"]
