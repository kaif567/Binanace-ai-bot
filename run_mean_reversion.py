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

def backtest_mr(df, trade_amount=100, fee=0.001):
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    
    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands (20, 2)
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - (2 * df['bb_std'])
    df['bb_upper'] = df['bb_mid'] + (2 * df['bb_std'])
    
    # SHIFT(1) FOR NO LOOKAHEAD BIAS
    df['rsi_prev'] = df['rsi'].shift(1)
    df['bb_lower_prev'] = df['bb_lower'].shift(1)
    df['bb_upper_prev'] = df['bb_upper'].shift(1)
    df['close_prev'] = df['close'].shift(1)
    
    history = []
    position = None
    entry_price = 0; stop_price = 0; target_price = 0
    
    # Simple Mean Reversion exits: Tight TP because mean reversion moves are short-lived
    TP_PCT = 0.03
    SL_PCT = 0.03
    
    for i in range(100, len(df)):
        current = df.iloc[i]
        c, h, l, o = current["close"], current["high"], current["low"], current["open"]
        rsi_prev, bb_l_prev, bb_u_prev, c_prev = current['rsi_prev'], current['bb_lower_prev'], current['bb_upper_prev'], current['close_prev']
        
        if pd.isna(rsi_prev) or pd.isna(bb_l_prev): continue
            
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
                history.append({"profit": net_profit, "gross_profit": gross_profit})
                position = None
                
        if position is None:
            # Entry rules
            if c_prev < bb_l_prev and rsi_prev < 30:
                position = "LONG"
                entry_price = c
                stop_price = c * (1 - SL_PCT)
                target_price = c * (1 + TP_PCT)
            elif c_prev > bb_u_prev and rsi_prev > 70:
                position = "SHORT"
                entry_price = c
                stop_price = c * (1 + SL_PCT)
                target_price = c * (1 - TP_PCT)
                
    return history

def run():
    print("="*80)
    for w in WINDOWS:
        all_trades = []
        print(f"Running {w['name']} for 4 coins...")
        for coin in COINS:
            df = fetch_window(coin, w["start"], w["end"])
            trades = backtest_mr(df)
            all_trades.extend(trades)
            
        n = len(all_trades)
        wins = [t for t in all_trades if t["profit"] > 0]
        wr = len(wins) / n if n > 0 else 0
        gross_profit = sum(t["gross_profit"] for t in all_trades if t["profit"] > 0)
        gross_loss = abs(sum(t["profit"] for t in all_trades if t["profit"] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        if n > 0:
            profits_array = np.array([t["profit"] for t in all_trades])
            sim_pfs = []
            for _ in range(10000):
                sample_p = np.random.choice(profits_array, size=n, replace=True)
                sgp = np.sum(sample_p[sample_p > 0])
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
