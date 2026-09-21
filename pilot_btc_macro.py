import sys, time
import pandas as pd
import math
import numpy as np
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines
import time

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

WINDOWS = [
    {"name": "Regime 1 (2020: COVID & Early Bull)", "start": ts(2020, 1, 1), "end": ts(2020, 12, 31)},
    {"name": "Regime 2 (2021: Massive Bull)", "start": ts(2021, 1, 1), "end": ts(2021, 12, 31)},
    {"name": "Regime 3 (2022: Bear & FTX Crash)", "start": ts(2022, 1, 1), "end": ts(2022, 12, 31)},
    {"name": "Regime 4 (2023: Chop & Recovery)", "start": ts(2023, 1, 1), "end": ts(2023, 12, 31)},
    {"name": "Regime 5 (2024: Post-ETF Bull)", "start": ts(2024, 1, 1), "end": ts(2024, 8, 31)}
]

def fetch_safe_chunked(symbol, interval, ms_per_candle):
    print(f"Fetching {symbol} {interval} data (2020-2024) in 6-month chunks...")
    all_pages = []
    chunk_ms = int(182.5 * 24 * 3600 * 1000) # ~6 months
    current_start = ts(2020, 1, 1)
    end_date = ts(2024, 8, 31)
    
    while current_start < end_date:
        chunk_end = min(current_start + chunk_ms, end_date)
        while True:
            raw = _fetch_klines_page(symbol=symbol, interval=interval, limit=1000, start_time=current_start, end_time=chunk_end)
            if not raw: break
            all_pages.extend(raw)
            current_start = int(raw[-1][0]) + ms_per_candle
            if current_start > chunk_end: break
            
        print(f"  Downloaded up to {datetime.fromtimestamp(chunk_end/1000, tz=timezone.utc).strftime('%Y-%m-%d')}...")
        time.sleep(0.5) # Thermal/Rate-limit safety
        current_start = chunk_end + ms_per_candle
        
    df = _normalize_klines(all_pages)
    return df

def backtest_donchian_atr(df, trade_amount=100, fee=0.001):
    if len(df) < 50: return []
    df = df.copy()
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    
    df["dh_20"] = df["high"].rolling(20).max().shift(1)
    df["dl_20"] = df["low"].rolling(20).min().shift(1)
    
    df['prev_close'] = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['prev_close']).abs()
    tr3 = (df['low'] - df['prev_close']).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean().shift(1)
    
    history = []
    position = None
    entry_price = 0; stop_price = 0; target_price = 0
    
    for i in range(25, len(df)):
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
                history.append({"profit": net_profit, "gross_profit": gross_profit})
                position = None
                
        if position is None:
            if c > dh:
                position = "LONG"; entry_price = c; stop_price = c - (2 * atr); target_price = c + (5 * atr)
            elif c < dl:
                position = "SHORT"; entry_price = c; stop_price = c + (2 * atr); target_price = c - (5 * atr)
                
    return history

def analyze_window(trades, w_name):
    n = len(trades)
    wins = [t for t in trades if t["profit"] > 0]
    wr = len(wins) / n if n > 0 else 0
    gross_profit = sum(t["gross_profit"] for t in trades if t["profit"] > 0)
    gross_loss = abs(sum(t["profit"] for t in trades if t["profit"] < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    if n > 0:
        profits_array = np.array([t["profit"] for t in trades])
        sim_pfs = []
        for _ in range(10000):
            sample_p = np.random.choice(profits_array, size=n, replace=True)
            sgp = np.sum(sample_p[sample_p > 0])
            sgl = np.sum(np.abs(sample_p[sample_p < 0]))
            sgl = sgl if sgl > 0 else 0.0001
            sim_pfs.append(sgp / sgl)
            
        pf_p025 = np.percentile(sim_pfs, 2.5)
    else:
        pf_p025 = 0
        
    return f"{w_name:<35} | Trades: {n:<4} | WR: {wr*100:>5.1f}% | PF: {pf:>4.2f} | 95% CI Lower: {pf_p025:>4.2f} | {'✅' if pf_p025 >= 0.95 else '❌'}"

def run():
    start_time = time.time()
    
    # 1. Fetching Pilot Data
    df_1h = fetch_safe_chunked("BTCUSDT", "1h", 3_600_000)
    df_4h = fetch_safe_chunked("BTCUSDT", "4h", 14_400_000)
    
    fetch_time = time.time() - start_time
    print(f"\n✅ Data fetching complete in {fetch_time:.1f} seconds. Running backtests...\n")
    
    # 2. Testing
    print("="*90)
    print("BTC-ONLY PILOT TEST: 1H Timeframe (Donchian-20 ATR-Exits)")
    print("-" * 90)
    for w in WINDOWS:
        mask = (df_1h['time'] >= w['start']) & (df_1h['time'] <= w['end'])
        df_sub = df_1h.loc[mask]
        trades = backtest_donchian_atr(df_sub)
        print(analyze_window(trades, w['name']))
        
    print("\n" + "="*90)
    print("BTC-ONLY PILOT TEST: 4H Timeframe (Donchian-20 ATR-Exits)")
    print("-" * 90)
    for w in WINDOWS:
        mask = (df_4h['time'] >= w['start']) & (df_4h['time'] <= w['end'])
        df_sub = df_4h.loc[mask]
        trades = backtest_donchian_atr(df_sub)
        print(analyze_window(trades, w['name']))
    print("="*90)
    
    total_time = time.time() - start_time
    print(f"\nTotal CPU/Execution Time: {total_time:.1f} seconds. (Safe and Lightweight)")

if __name__ == "__main__":
    run()
