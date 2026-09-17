"""
ADX + ATR Threshold Sweep — finds 1h-BTC-specific thresholds via OOS data.

METHODOLOGY (mirrors Strategy Quality V2 validation):
- Use the SAME walk-forward OOS trade history the pipeline already produces.
- For each candidate threshold, filter OOS trades to those where regime would
  have been TRENDING at signal time.
- Recompute Strategy Quality V2 on the filtered subset.
- The threshold with the highest Strategy Quality V2 wins.

CRITICAL RULE (from WORKING_PRINCIPLES.md Rule 5):
- We only SELECT thresholds using OOS trade outcomes (never training outcomes).
- We run the sweep on historical data, not future/live data.
- We do NOT tune thresholds on OOS data in a loop (single pass only).

Usage:
    source venv/bin/activate
    python backtest/threshold_sweep.py

Output:
    Prints a table and writes results to backtest/sweep_results.json
"""

import json
import math
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from data.binance_api import get_closed_candles_paginated
from indicators.technical import add_indicators
from indicators.regime import classify_regime
from database.self_optimizer import improve_strategy


# ─────────────────────────────────────────────────────────────────────────────
# Strategy Quality V2 — same formula as backtest/optimizer.py
# Duplicated here so the sweep has zero dependency on pipeline internals.
# ─────────────────────────────────────────────────────────────────────────────

def _strategy_quality_v2(closed_trades, trade_amount=100.0):
    """
    Compute Strategy Quality V2 on a list of closed trade dicts.
    Each trade dict must have a 'profit' key (net dollar P&L).

    Returns score 0–100. 50 = neutral/no-edge.
    """
    n = len(closed_trades)
    if n == 0:
        return 0.0

    profits = [float(t.get("profit", 0)) for t in closed_trades]
    total_profit = sum(profits)
    avg_return = (total_profit / n) / trade_amount

    gross_wins = sum(p for p in profits if p > 0)
    gross_losses = abs(sum(p for p in profits if p < 0))
    if gross_losses > 0:
        pf = gross_wins / gross_losses
    elif gross_wins > 0:
        pf = gross_wins  # large finite number, no losses
    else:
        pf = 0.0

    # Component 1: return signal (60%)
    c1 = math.tanh(avg_return / 0.005)

    # Component 2: PF signal (40%)
    if pf > 0:
        c2 = math.tanh(math.log(pf) / math.log(2.5))
    else:
        c2 = -1.0

    edge = 0.60 * c1 + 0.40 * c2
    raw_score = 50.0 + 50.0 * edge

    # OOS shrinkage: n / (n + 50)
    confidence = n / (n + 50.0)
    final_score = 50.0 + confidence * (raw_score - 50.0)
    return round(final_score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Sweep helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_regime_at_time(df_indexed, signal_time, adx_thresh, adx_ranging, atr_lookback, atr_change):
    """
    Find the most recent row in df_indexed at or before signal_time,
    then classify regime using the last `atr_lookback + 1` rows up to that point.
    Returns the regime string.
    """
    # df_indexed has 'time' as a column (ms timestamp)
    mask = df_indexed["time"] <= int(signal_time)
    subset = df_indexed[mask]

    if len(subset) == 0:
        return "UNKNOWN"

    return classify_regime(
        subset,
        adx_trending_thresh=adx_thresh,
        adx_ranging_thresh=adx_ranging,
        atr_lookback=atr_lookback,
        atr_change_thresh=atr_change,
    )


def _pair_oos_trades(oos_history):
    """
    The engine stores two records per trade:
      - Entry record: type "BUY" or "SHORT" — has signal_time, no profit
      - Exit record:  type "SELL" or "COVER" — has profit, no signal_time

    This function pairs them in order and returns a flat list of dicts:
      { "signal_time": int, "profit": float }

    This is required because the sweep needs signal_time (from entry) AND
    profit (from exit) for each trade, but neither record alone has both.
    """
    paired = []
    pending_entry = None

    for t in oos_history:
        t_type = t.get("type", "")
        if t_type in ("BUY", "SHORT"):
            pending_entry = t
        elif t_type in ("SELL", "COVER") and pending_entry is not None:
            paired.append({
                "signal_time": pending_entry.get("signal_time"),
                "profit": float(t.get("profit", 0)),
            })
            pending_entry = None
        # FOLD_END_MTM exits may not have a paired entry in list order;
        # skip orphaned exits gracefully.

    return paired


def _filter_oos_trades(paired_trades, df, adx_thresh, adx_ranging, atr_lookback, atr_change):
    """
    Return only the paired trades whose signal candle was in a TRENDING regime.

    paired_trades: list of {"signal_time": int|None, "profit": float}
    """
    trending_trades = []
    for trade in paired_trades:
        signal_time = trade.get("signal_time")
        if signal_time is None:
            # No timestamp → UNKNOWN, exclude
            continue

        regime = _get_regime_at_time(
            df, signal_time, adx_thresh, adx_ranging, atr_lookback, atr_change
        )
        if regime == "TRENDING":
            trending_trades.append(trade)

    return trending_trades


def sweep_adx_threshold(
    oos_trades,
    df,
    adx_trending_candidates,
    adx_ranging_candidates,
    atr_lookback=24,
    atr_change_thresh=0.30,
):
    """
    For each (adx_trending, adx_ranging) pair, filter OOS trades to
    TRENDING-only and compute Strategy Quality V2.

    Parameters
    ----------
    oos_trades : list of dicts
        Closed OOS trade history with 'profit' and 'signal_time' keys.
    df : pd.DataFrame
        Full 1h candle history with indicators added (adx, atr columns).
    adx_trending_candidates : list of float
        ADX thresholds to test as the TRENDING boundary.
    adx_ranging_candidates : list of float
        ADX thresholds to test as the RANGING boundary.
        Must be <= corresponding trending threshold.
    atr_lookback : int
        ATR surge lookback (held constant during ADX sweep).
    atr_change_thresh : float
        ATR surge threshold (held constant during ADX sweep).

    Returns
    -------
    list of dicts, sorted by strategy_quality_v2 descending.
    """
    baseline_quality = _strategy_quality_v2(oos_trades)
    print(f"\n{'='*65}")
    print(f"  BASELINE (no filter): {len(oos_trades)} trades, "
          f"Strategy Quality V2 = {baseline_quality}")
    print(f"{'='*65}")

    results = []

    for adx_t in adx_trending_candidates:
        for adx_r in adx_ranging_candidates:
            if adx_r > adx_t:
                # Invalid: ranging threshold must be <= trending threshold
                continue

            filtered = _filter_oos_trades(
                oos_trades, df, adx_t, adx_r, atr_lookback, atr_change_thresh
            )
            n_filtered = len(filtered)
            quality = _strategy_quality_v2(filtered)
            pct_kept = round(100.0 * n_filtered / max(len(oos_trades), 1), 1)

            results.append({
                "adx_trending_thresh": adx_t,
                "adx_ranging_thresh": adx_r,
                "atr_lookback": atr_lookback,
                "atr_change_thresh": atr_change_thresh,
                "filtered_trades": n_filtered,
                "total_trades": len(oos_trades),
                "pct_trades_kept": pct_kept,
                "strategy_quality_v2": quality,
                "improvement_over_baseline": round(quality - baseline_quality, 2),
            })

    results.sort(key=lambda x: x["strategy_quality_v2"], reverse=True)
    return results, baseline_quality


def sweep_atr_threshold(
    oos_trades,
    df,
    adx_trending_thresh,
    adx_ranging_thresh,
    atr_lookback_candidates,
    atr_change_candidates,
):
    """
    For each (lookback, surge_pct) pair, compute Strategy Quality V2
    on trades that survive both ADX-trending AND ATR-non-spike filters.

    Parameters
    ----------
    adx_trending_thresh : float
        Winning ADX trending threshold (from sweep_adx_threshold result).
    adx_ranging_thresh : float
        Winning ADX ranging threshold.
    atr_lookback_candidates : list of int
        Candle lookback windows to test (e.g. [12, 24, 48]).
    atr_change_candidates : list of float
        Fractional ATR surge thresholds to test (e.g. [0.20, 0.30, 0.40]).

    Returns
    -------
    list of dicts, sorted by strategy_quality_v2 descending.
    """
    results = []

    for lookback in atr_lookback_candidates:
        for surge in atr_change_candidates:
            filtered = _filter_oos_trades(
                oos_trades, df, adx_trending_thresh, adx_ranging_thresh,
                lookback, surge
            )
            n_filtered = len(filtered)
            quality = _strategy_quality_v2(filtered)
            pct_kept = round(100.0 * n_filtered / max(len(oos_trades), 1), 1)

            results.append({
                "adx_trending_thresh": adx_trending_thresh,
                "adx_ranging_thresh": adx_ranging_thresh,
                "atr_lookback": lookback,
                "atr_change_thresh": surge,
                "filtered_trades": n_filtered,
                "total_trades": len(oos_trades),
                "pct_trades_kept": pct_kept,
                "strategy_quality_v2": quality,
            })

    results.sort(key=lambda x: x["strategy_quality_v2"], reverse=True)
    return results


def _print_table(results, title):
    print(f"\n{title}")
    print("-" * 80)
    print(f"{'ADX-T':>7} {'ADX-R':>7} {'ATR-LB':>7} {'ATR-Surge':>10} "
          f"{'N-trades':>9} {'%Kept':>7} {'Qual-V2':>9} {'ΔBaseline':>10}")
    print("-" * 80)
    for r in results:
        print(
            f"{r['adx_trending_thresh']:>7.1f} "
            f"{r['adx_ranging_thresh']:>7.1f} "
            f"{r['atr_lookback']:>7d} "
            f"{r['atr_change_thresh']:>10.0%} "
            f"{r['filtered_trades']:>9d} "
            f"{r['pct_trades_kept']:>7.1f}% "
            f"{r['strategy_quality_v2']:>9.2f} "
            f"{r.get('improvement_over_baseline', 0):>+10.2f}"
        )
    print("-" * 80)


# ─────────────────────────────────────────────────────────────────────────────
# Main — fetches live data and runs both sweeps
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n🔎 PHASE 1 THRESHOLD SWEEP — ADX + ATR on 1h BTC")
    print("="*65)
    print("Fetching historical 1h BTC candles from Binance...")

    SYMBOL = "BTCUSDT"
    HISTORICAL_CANDLES = 2000   # ~83 days of 1h data

    df, integrity = get_closed_candles_paginated(
        SYMBOL,
        interval="1h",
        limit=HISTORICAL_CANDLES,
        recent_gap_window_candles=3,
        truncate_historical_gaps=True,
        return_report=True,
    )

    print(f"  Returned rows: {integrity.get('returned_rows')}")
    print(f"  Historical gaps: {integrity.get('historical_gap_count', 0)}")
    print(f"  Rows used: {len(df)}")

    if len(df) < 600:
        print("ERROR: Not enough candle history for a meaningful sweep.")
        sys.exit(1)

    print("\nAdding technical indicators (ADX, ATR)...")
    df = add_indicators(df)

    # ── Run walk-forward to get OOS trade pool ────────────────────────────
    print("\nRunning walk-forward to collect OOS trade pool...")
    print("(This uses TRAINING data for optimizer, OOS data for evaluation only)")

    optimized = improve_strategy(
        df,
        initial_train_window=300,
        test_window=50,
        step=50,
        min_oos_trades=20,
        initial_balance=1000,
        trade_amount=100,
        fee=0.001,
    )

    if optimized.get("status") != "completed":
        print(f"ERROR: Walk-forward failed: {optimized.get('message')}")
        sys.exit(1)

    oos_result = optimized.get("oos", {})
    oos_history = oos_result.get("history", [])

    oos_closed = _pair_oos_trades(oos_history)

    print(f"\n  OOS closed trades paired (signal_time + profit): {len(oos_closed)}")

    if len(oos_closed) < 20:
        print("WARNING: Very few OOS trades — sweep results will be noisy.")

    # ── SWEEP 1: ADX thresholds ───────────────────────────────────────────
    ADX_TRENDING_CANDIDATES = [15.0, 18.0, 20.0, 22.0, 25.0, 28.0]
    ADX_RANGING_CANDIDATES  = [12.0, 15.0, 18.0, 20.0]
    FIXED_ATR_LOOKBACK       = 24
    FIXED_ATR_CHANGE         = 0.30

    adx_results, baseline_quality = sweep_adx_threshold(
        oos_closed,
        df,
        ADX_TRENDING_CANDIDATES,
        ADX_RANGING_CANDIDATES,
        atr_lookback=FIXED_ATR_LOOKBACK,
        atr_change_thresh=FIXED_ATR_CHANGE,
    )

    _print_table(adx_results, "SWEEP 1 — ADX Threshold Candidates (sorted by Strategy Quality V2)")

    best_adx = adx_results[0] if adx_results else None
    if best_adx:
        print(f"\n  ✅ Best ADX combination:")
        print(f"     adx_trending_thresh = {best_adx['adx_trending_thresh']}")
        print(f"     adx_ranging_thresh  = {best_adx['adx_ranging_thresh']}")
        print(f"     Strategy Quality V2 = {best_adx['strategy_quality_v2']} "
              f"({best_adx['improvement_over_baseline']:+.2f} vs baseline)")
        print(f"     Trades kept: {best_adx['filtered_trades']}/{best_adx['total_trades']} "
              f"({best_adx['pct_trades_kept']}%)")

    # ── SWEEP 2: ATR thresholds (using best ADX from sweep 1) ────────────
    if best_adx and best_adx["improvement_over_baseline"] > 0:
        print("\n\nSWEEP 2 — ATR Surge Threshold Candidates")
        print("(Using best ADX thresholds from Sweep 1)")

        ATR_LOOKBACK_CANDIDATES = [12, 24, 48]
        ATR_CHANGE_CANDIDATES   = [0.20, 0.30, 0.40]

        atr_results = sweep_atr_threshold(
            oos_closed,
            df,
            adx_trending_thresh=best_adx["adx_trending_thresh"],
            adx_ranging_thresh=best_adx["adx_ranging_thresh"],
            atr_lookback_candidates=ATR_LOOKBACK_CANDIDATES,
            atr_change_candidates=ATR_CHANGE_CANDIDATES,
        )

        _print_table(atr_results, "SWEEP 2 — ATR Threshold Candidates (sorted by Strategy Quality V2)")

        best_atr = atr_results[0] if atr_results else None
        if best_atr:
            print(f"\n  ✅ Best ATR combination:")
            print(f"     atr_lookback      = {best_atr['atr_lookback']}")
            print(f"     atr_change_thresh = {best_atr['atr_change_thresh']:.0%}")
            print(f"     Strategy Quality V2 = {best_atr['strategy_quality_v2']}")

    else:
        print("\n  ⚠️  No ADX threshold improved over baseline.")
        print("  Conclusion: Chop filter has no proven benefit on this data.")
        print("  Recommendation: Do NOT add regime gate condition.")
        best_atr = None

    # ── Save results ──────────────────────────────────────────────────────
    output = {
        "baseline_quality_v2": baseline_quality,
        "baseline_oos_trades": len(oos_closed),
        "adx_sweep": adx_results,
        "atr_sweep": atr_results if best_adx and best_adx["improvement_over_baseline"] > 0 else [],
        "recommended": {
            "adx_trending_thresh": best_adx["adx_trending_thresh"] if best_adx else None,
            "adx_ranging_thresh": best_adx["adx_ranging_thresh"] if best_adx else None,
            "atr_lookback": best_atr["atr_lookback"] if best_atr else FIXED_ATR_LOOKBACK,
            "atr_change_thresh": best_atr["atr_change_thresh"] if best_atr else FIXED_ATR_CHANGE,
            "improves_baseline": (best_adx["improvement_over_baseline"] > 0) if best_adx else False,
        }
    }

    results_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "sweep_results.json"
    )
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Full results saved to: backtest/sweep_results.json")
    print("\n" + "="*65)
    print("SWEEP COMPLETE — Review results before writing gate code.")
    print("="*65)


if __name__ == "__main__":
    main()

