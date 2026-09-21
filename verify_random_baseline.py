import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines
from backtest.engine import run_advanced_backtest

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

WINDOWS = [
    {"name": "Aug 2023", "start": ts(2023, 8, 1), "end": ts(2023, 10, 31)},
    {"name": "Jan 2024", "start": ts(2024, 1, 1), "end": ts(2024, 3, 31)},
    {"name": "Mar 2024", "start": ts(2024, 3, 1), "end": ts(2024, 5, 31)},
    {"name": "Jun 2024", "start": ts(2024, 6, 1), "end": ts(2024, 8, 31)}
]

def fetch_window(start_ms, end_ms):
    pages = []
    current_start = start_ms
    while True:
        raw = _fetch_klines_page(
            symbol="BTCUSDT",
            interval="1h",
            limit=1000,
            start_time=current_start,
            end_time=end_ms,
        )
        if not raw: break
        pages.extend(raw)
        current_start = int(raw[-1][0]) + 3_600_000
        if current_start > end_ms: break
    return _normalize_klines(pages)

def format_row(window, run_label, trades, wr, pf, robustness, drop_top_2):
    return f"| {window:<9} | {run_label:<19} | {trades:<6} | {wr:<5.2f} | {pf:<5.2f} | {robustness:<11} | {drop_top_2:<13.2f} |"

def add_random_signals(df, seed=42):
    np.random.seed(seed)
    n = len(df)
    r = np.random.rand(n)
    
    signals = []
    scores = []
    # 2.5% frequency ~ 50 trades per 2000 candles
    for val in r:
        if val < 0.0125:
            signals.append("STRONG BUY")
            scores.append(100)
        elif val < 0.0250:
            signals.append("STRONG SELL")
            scores.append(0)
        else:
            signals.append("HOLD")
            scores.append(50)
            
    df["signal"] = signals
    df["score"] = scores
    return df

def run_tests():
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    
    table_lines = []
    table_lines.append("| Window    | Run                 | Trades | WR    | PF    | Robustness  | PF drop top-2 |")
    table_lines.append("|-----------|---------------------|--------|-------|-------|-------------|---------------|")

    for w in WINDOWS:
        sys.stderr.write(f"Fetching {w['name']}...\n")
        df = fetch_window(w["start"], w["end"])
        if df is None or len(df) == 0:
            continue
            
        # fixed random seed for reproducibility
        df = add_random_signals(df, seed=42)
        
        sys.stderr.write(f"  Running Random Baseline for {w['name']}...\n")
        
        # SINGLE BACKTEST PASS - No grid search, no walk forward
        try:
            res = run_advanced_backtest(
                df,
                initial_balance=1000,
                trade_amount=100,
                stop_loss=0.02,     # Fixed SL 2%
                take_profit=0.05,   # Fixed TP 5%
                fee=0.001,
                trade_start_index=1,
                force_close_at_end=True
            )
        except TypeError:
            # handle the donchian_period param we injected earlier if needed
            res = run_advanced_backtest(
                df,
                initial_balance=1000,
                trade_amount=100,
                stop_loss=0.02,
                take_profit=0.05,
                donchian_period=20,
                fee=0.001,
                trade_start_index=1,
                force_close_at_end=True
            )
            
        history = [t for t in res.get("history", []) if "profit" in t]
        
        trades = len(history)
        if trades < 3:
            table_lines.append(format_row(w["name"], "Random Seed=42", trades, 0, 0, "FAILED", 0))
            continue
            
        # Manual metrics calculation
        win_trades = len([t for t in history if t["profit"] > 0])
        wr = (win_trades / trades) * 100
        
        gross_profit = sum(t["gross_profit"] for t in history if t["profit"] > 0)
        gross_loss = abs(sum(t["profit"] for t in history if t["profit"] < 0))
        
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Robustness
        winners = sorted([t for t in history if t["profit"] > 0], key=lambda x: x["profit"], reverse=True)
        if len(winners) >= 2:
            top_2_profit = winners[0]["profit"] + winners[1]["profit"]
            ex_profit = gross_profit - top_2_profit
            ex_pf = ex_profit / gross_loss if gross_loss > 0 else 0
        else:
            ex_pf = pf
            
        if pf < 1.0:
            robustness = "FAILED"
        elif ex_pf >= 1.0:
            robustness = "ROBUST"
        else:
            robustness = "FRAGILE"
            
        table_lines.append(format_row(
            w["name"],
            "Random Seed=42",
            trades,
            wr,
            pf,
            robustness,
            ex_pf
        ))
    
    sys.stdout.close()
    sys.stdout = original_stdout
    
    print("\n\n" + "="*77)
    for line in table_lines:
        print(line)
    print("="*77 + "\n")

if __name__ == "__main__":
    run_tests()
