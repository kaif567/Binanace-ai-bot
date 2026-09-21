import sys
import pandas as pd
from datetime import datetime, timezone
from verify_donchian_light import fetch_window, WINDOWS, format_time, format_row
from indicators.technical import add_indicators
from backtest.validation import walk_forward_test

for w in WINDOWS:
    if w["name"] not in ["Aug 2023", "Mar 2024", "Jun 2024"]: continue
    df = fetch_window(w["start"], w["end"])
    df = add_indicators(df)
    res = walk_forward_test(
        df, initial_train_window=300, test_window=100, step=100,
        min_oos_trades=10, donchian_period=20
    )
    history = [t for t in res.get("history", []) if "profit" in t]
    if not history: continue
    
    gross_profit = sum(t["gross_profit"] for t in history if t["profit"] > 0)
    gross_loss = abs(sum(t["profit"] for t in history if t["profit"] < 0))
    
    winners = sorted([t for t in history if t["profit"] > 0], key=lambda x: x["profit"], reverse=True)
    if len(winners) >= 2:
        top1 = winners[0]
        top2 = winners[1]
        print(f"--- {w['name']} ---")
        print(f"Total Gross Profit: {gross_profit:.2f}% | Gross Loss: {gross_loss:.2f}% | Total PF: {(gross_profit/gross_loss) if gross_loss>0 else 0:.2f}")
        print(f"  Top 1 Trade: {top1['profit']:.2f}% ({top1['profit']/gross_profit*100:.1f}% of all gross profit) | Exit: {format_time(top1.get('exit_time', 0))} @ {top1.get('exit_price', 0):.1f} | Reason: {top1.get('exit_reason', '')}")
        print(f"  Top 2 Trade: {top2['profit']:.2f}% ({top2['profit']/gross_profit*100:.1f}% of all gross profit) | Exit: {format_time(top2.get('exit_time', 0))} @ {top2.get('exit_price', 0):.1f} | Reason: {top2.get('exit_reason', '')}")
        ex_top2_profit = gross_profit - top1["profit"] - top2["profit"]
        ex_top2_pf = ex_top2_profit / gross_loss if gross_loss > 0 else 0
        print(f"  PF Without Top 2: {ex_top2_pf:.2f}")
        print("")
