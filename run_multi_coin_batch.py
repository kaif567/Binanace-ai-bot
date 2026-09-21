import sys
import pandas as pd
import math
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
# Batch 1 Window
WINDOW = {"name": "Jun 2024 (Chop)", "start": ts(2024, 6, 1), "end": ts(2024, 8, 31)}

def fetch_window(symbol, start_ms, end_ms):
    pages = []
    current_start = start_ms
    while True:
        raw = _fetch_klines_page(symbol=symbol, interval="1h", limit=1000, start_time=current_start, end_time=end_ms)
        if not raw: break
        pages.extend(raw)
        current_start = int(raw[-1][0]) + 3_600_000
        if current_start > end_ms: break
    return _normalize_klines(pages)

def backtest_donchian(df, trade_amount=100, fee=0.001):
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    df["dh_20"] = df["high"].rolling(20).max().shift(1)
    df["dl_20"] = df["low"].rolling(20).min().shift(1)
    
    history = []
    position = None
    entry_price = 0; stop_price = 0; target_price = 0
    
    for i in range(100, len(df)):
        current = df.iloc[i]
        c, h, l, o = current["close"], current["high"], current["low"], current["open"]
        dh, dl = current["dh_20"], current["dl_20"]
        
        if pd.isna(dh): continue
            
        if position is not None:
            exit_reason = None
            if position == "LONG":
                if o <= stop_price: exit_reason = "SL_GAP"; exit_price = o
                elif o > target_price: exit_reason = "TP_GAP"; exit_price = o
                elif l <= stop_price: exit_reason = "SL"; exit_price = stop_price
                elif h > target_price: exit_reason = "TP"; exit_price = target_price
            else:
                if o >= stop_price: exit_reason = "SL_GAP"; exit_price = o
                elif o < target_price: exit_reason = "TP_GAP"; exit_price = o
                elif h >= stop_price: exit_reason = "SL"; exit_price = stop_price
                elif l < target_price: exit_reason = "TP"; exit_price = target_price
                
            if exit_reason:
                if position == "LONG": gross_return = (exit_price - entry_price) / entry_price
                else: gross_return = (entry_price - exit_price) / entry_price
                gross_profit = trade_amount * gross_return
                net_profit = gross_profit - (trade_amount * fee * 2)
                history.append({"profit": net_profit, "gross_profit": gross_profit, "type": position, "return": gross_return})
                position = None
                
        if position is None:
            if c > dh:
                position = "LONG"; entry_price = c; stop_price = c*0.98; target_price = c*1.05
            elif c < dl:
                position = "SHORT"; entry_price = c; stop_price = c*1.02; target_price = c*0.95
                
    return history

def run_batch():
    all_trades = []
    print(f"Running Batch 1: {WINDOW['name']} for {len(COINS)} coins...")
    for coin in COINS:
        df = fetch_window(coin, WINDOW["start"], WINDOW["end"])
        trades = backtest_donchian(df)
        all_trades.extend(trades)
        print(f"  {coin}: {len(trades)} trades")
        
    n = len(all_trades)
    wins = [t for t in all_trades if t["profit"] > 0]
    wr = len(wins) / n if n > 0 else 0
    
    gross_profit = sum(t["gross_profit"] for t in all_trades if t["profit"] > 0)
    gross_loss = abs(sum(t["profit"] for t in all_trades if t["profit"] < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Calculate CI for True WR
    z = 1.96
    se = math.sqrt((wr * (1 - wr)) / n) if n > 0 else 0
    lower_wr = wr - z * se
    upper_wr = wr + z * se
    
    print("\n" + "="*80)
    print(f"BATCH 1 RESULTS: {WINDOW['name']} (Portfolio: {', '.join(COINS)})")
    print(f"Total Trades (Sample Size): {n}")
    print(f"Win Rate: {wr*100:.2f}% (95% CI: [{lower_wr*100:.2f}% - {upper_wr*100:.2f}%])")
    print(f"Profit Factor (PF): {pf:.2f}")
    
    # CI for PF (Simulation approach)
    import numpy as np
    tp = 5.0; sl = 2.0
    wins_sim = np.random.binomial(n, wr, size=100000)
    losses_sim = n - wins_sim
    sim_gross_profits = wins_sim * tp
    sim_gross_losses = losses_sim * sl
    sim_gross_losses = np.where(sim_gross_losses == 0, 0.0001, sim_gross_losses)
    sim_pfs = sim_gross_profits / sim_gross_losses
    pf_p05 = np.percentile(sim_pfs, 5)
    pf_p95 = np.percentile(sim_pfs, 95)
    
    print(f"90% Confidence Interval for PF: [{pf_p05:.2f} to {pf_p95:.2f}]")
    if pf_p05 >= 0.95:
        print("Robustness: PASSED ✅ (Lower bound of PF is >= 0.95)")
    else:
        print("Robustness: FAILED ❌ (Lower bound of PF is < 0.95)")
    print("="*80)

if __name__ == "__main__":
    run_batch()
