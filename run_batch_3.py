import sys
import pandas as pd
import math
import numpy as np
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
BATCH3 = {"name": "Jan 2024 (Bull Start)", "start": ts(2024, 1, 1), "end": ts(2024, 3, 31)}

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
                history.append({"profit": net_profit, "gross_profit": gross_profit})
                position = None
                
        if position is None:
            if c > dh:
                position = "LONG"; entry_price = c; stop_price = c*0.98; target_price = c*1.05
            elif c < dl:
                position = "SHORT"; entry_price = c; stop_price = c*1.02; target_price = c*0.95
                
    return history

def run():
    all_trades = []
    print(f"Running Batch 3: {BATCH3['name']} for 4 coins...")
    for coin in COINS:
        df = fetch_window(coin, BATCH3["start"], BATCH3["end"])
        trades = backtest_donchian(df)
        all_trades.extend(trades)
        print(f"  {coin}: {len(trades)} trades")
        
    n = len(all_trades)
    wins = [t for t in all_trades if t["profit"] > 0]
    wr = len(wins) / n if n > 0 else 0
    gross_profit = sum(t["gross_profit"] for t in all_trades if t["profit"] > 0)
    gross_loss = abs(sum(t["profit"] for t in all_trades if t["profit"] < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    wins_sim = np.random.binomial(n, wr, size=100000)
    sim_gross_profits = wins_sim * 5.0
    sim_gross_losses = (n - wins_sim) * 2.0
    sim_gross_losses = np.where(sim_gross_losses == 0, 0.0001, sim_gross_losses)
    sim_pfs = sim_gross_profits / sim_gross_losses
    pf_p025 = np.percentile(sim_pfs, 2.5)
    pf_p975 = np.percentile(sim_pfs, 97.5)
    
    print("\n" + "="*80)
    print(f"BATCH 3 RESULTS: {BATCH3['name']} (Portfolio: BTC, ETH, BNB, SOL)")
    print(f"Total Trades (Sample Size): {n}")
    print(f"Win Rate: {wr*100:.2f}%")
    print(f"Profit Factor (PF): {pf:.2f}")
    print(f"95% Confidence Interval for PF: [{pf_p025:.2f} to {pf_p975:.2f}]")
    if pf_p025 >= 0.95:
        print("Robustness: PASSED ✅ (Lower bound of PF is >= 0.95)")
    else:
        print("Robustness: FAILED ❌ (Lower bound of PF is < 0.95)")
    print("="*80)

if __name__ == "__main__":
    run()
