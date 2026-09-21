import sys
import pandas as pd
import math
import numpy as np
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
WINDOWS = [
    {"name": "Batch 3 (Jan 2024 Bull Start)", "start": ts(2024, 1, 1), "end": ts(2024, 3, 31)},
    {"name": "Batch 2 (Mar 2024 Bull)", "start": ts(2024, 3, 1), "end": ts(2024, 5, 31)},
    {"name": "Batch 1 (Jun 2024 Chop)", "start": ts(2024, 6, 1), "end": ts(2024, 8, 31)}
]

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

def backtest_donchian_atr(df, trade_amount=100, fee=0.001):
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    
    # INDEPENDENT SHIFT(1): No lookahead bias
    df["dh_20"] = df["high"].rolling(20).max().shift(1)
    df["dl_20"] = df["low"].rolling(20).min().shift(1)
    
    # Calculate TR and ATR(14) with SHIFT(1)
    df['prev_close'] = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['prev_close']).abs()
    tr3 = (df['low'] - df['prev_close']).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean().shift(1)
    
    history = []
    position = None
    entry_price = 0; stop_price = 0; target_price = 0
    
    for i in range(100, len(df)):
        current = df.iloc[i]
        c, h, l, o, atr = current["close"], current["high"], current["low"], current["open"], current["atr"]
        dh, dl = current["dh_20"], current["dl_20"]
        
        if pd.isna(dh) or pd.isna(atr): continue
            
        if position is not None:
            exit_reason = None
            if position == "LONG":
                if o <= stop_price: exit_reason = "SL_GAP"; exit_price = o
                elif o >= target_price: exit_reason = "TP_GAP"; exit_price = o
                elif l <= stop_price: exit_reason = "SL"; exit_price = stop_price
                elif h >= target_price: exit_reason = "TP"; exit_price = target_price
            else:
                if o >= stop_price: exit_reason = "SL_GAP"; exit_price = o
                elif o <= target_price: exit_reason = "TP_GAP"; exit_price = o
                elif h >= stop_price: exit_reason = "SL"; exit_price = stop_price
                elif l <= target_price: exit_reason = "TP"; exit_price = target_price
                
            if exit_reason:
                if position == "LONG": gross_return = (exit_price - entry_price) / entry_price
                else: gross_return = (entry_price - exit_price) / entry_price
                gross_profit = trade_amount * gross_return
                net_profit = gross_profit - (trade_amount * fee * 2)
                history.append({"profit": net_profit, "gross_profit": gross_profit, "return": gross_return})
                position = None
                
        if position is None:
            if c > dh:
                position = "LONG"; entry_price = c
                stop_price = c - (2 * atr)
                target_price = c + (5 * atr)
            elif c < dl:
                position = "SHORT"; entry_price = c
                stop_price = c + (2 * atr)
                target_price = c - (5 * atr)
                
    return history

def run():
    print("="*80)
    for w in WINDOWS:
        all_trades = []
        print(f"Running {w['name']} for 4 coins...")
        for coin in COINS:
            df = fetch_window(coin, w["start"], w["end"])
            trades = backtest_donchian_atr(df)
            all_trades.extend(trades)
            # print(f"  {coin}: {len(trades)} trades")
            
        n = len(all_trades)
        wins = [t for t in all_trades if t["profit"] > 0]
        wr = len(wins) / n if n > 0 else 0
        gross_profit = sum(t["gross_profit"] for t in all_trades if t["profit"] > 0)
        gross_loss = abs(sum(t["profit"] for t in all_trades if t["profit"] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Monte Carlo CI for dynamic sizes
        # We can't use fixed TP/SL binomial anymore because returns vary per trade dynamically
        # We will use bootstrap resampling to find the 95% CI of the PF
        if n > 0:
            profits_array = np.array([t["profit"] for t in all_trades])
            gross_profits_array = np.array([t["gross_profit"] for t in all_trades if t["profit"] > 0])
            gross_losses_array = np.array([abs(t["profit"]) for t in all_trades if t["profit"] < 0])
            
            sim_pfs = []
            for _ in range(10000):
                # Sample with replacement
                sample_p = np.random.choice(profits_array, size=n, replace=True)
                sgp = np.sum(sample_p[sample_p > 0]) # rough gross profit (includes fees in reality but fine for bounds)
                sgl = np.sum(np.abs(sample_p[sample_p < 0]))
                sgl = sgl if sgl > 0 else 0.0001
                sim_pfs.append(sgp / sgl)
                
            pf_p025 = np.percentile(sim_pfs, 2.5)
            pf_p975 = np.percentile(sim_pfs, 97.5)
        else:
            pf_p025, pf_p975 = 0, 0
            
        print(f"RESULTS: {w['name']}")
        print(f"Total Trades: {n} | Win Rate: {wr*100:.2f}% | Expected PF: {pf:.2f}")
        print(f"95% Confidence Interval for PF: [{pf_p025:.2f} to {pf_p975:.2f}]")
        if pf_p025 >= 0.95:
            print("Robustness: PASSED ✅ (Lower bound >= 0.95)")
        else:
            print("Robustness: FAILED ❌")
        print("-" * 80)

if __name__ == "__main__":
    run()
