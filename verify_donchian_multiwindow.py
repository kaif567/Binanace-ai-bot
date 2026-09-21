import sys
import os
import pandas as pd
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines
from indicators.technical import add_indicators
from backtest.validation import walk_forward_test

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

WINDOWS = [
    {
        "name": "Aug 2023",
        "start": ts(2023, 8, 1),
        "end": ts(2023, 10, 31)
    },
    {
        "name": "Jan 2024",
        "start": ts(2024, 1, 1),
        "end": ts(2024, 3, 31)
    },
    {
        "name": "Mar 2024",
        "start": ts(2024, 3, 1),
        "end": ts(2024, 5, 31)
    }
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

def format_row(window, run_label, trades, wr, pf, sq_v2, robustness, drop_top_2):
    return f"| {window:<9} | {run_label:<19} | {trades:<6} | {wr:<5.2f} | {pf:<5.2f} | {sq_v2:<5.2f} | {robustness:<11} | {drop_top_2:<13.2f} |"

def run_tests():
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    
    table_lines = []
    table_lines.append("| Window    | Run                 | Trades | WR    | PF    | SQ V2 | Robustness  | PF drop top-2 |")
    table_lines.append("|-----------|---------------------|--------|-------|-------|-------|-------------|---------------|")

    for w in WINDOWS:
        sys.stderr.write(f"Fetching {w['name']}...\n")
        df = fetch_window(w["start"], w["end"])
        if df is None or len(df) == 0:
            continue
        df = add_indicators(df)
        
        sys.stderr.write(f"  Running Donchian Breakout for {w['name']}...\n")
        res = walk_forward_test(
            df, 
            initial_train_window=300, 
            test_window=100, 
            step=100, 
            min_oos_trades=10
        )
        
        if res.get("status") == "failed" or res.get("trades", 0) == 0:
            table_lines.append(format_row(w["name"], "Donchian Breakout", 0, 0, 0, 0, "FAILED", 0))
        else:
            table_lines.append(format_row(
                w["name"],
                "Donchian Breakout",
                res.get("trades", 0),
                res.get("win_rate", 0),
                res.get("profit_factor", 0),
                res.get("strategy_quality", 0),
                res.get("robustness_status", "UNKNOWN"),
                res.get("robustness", {}).get("pf_ex_top2", 0.0)
            ))
    
    sys.stdout.close()
    sys.stdout = original_stdout
    
    print("\n\n" + "="*85)
    for line in table_lines:
        print(line)
    print("="*85 + "\n")

if __name__ == "__main__":
    run_tests()
