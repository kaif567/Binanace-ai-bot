import sys
import os
import pandas as pd
import ta
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines

def ts(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

def fetch_window(start_ms, end_ms):
    pages = []
    current_start = start_ms
    while True:
        raw = _fetch_klines_page(symbol="BTCUSDT", interval="1h", limit=1000, start_time=current_start, end_time=end_ms)
        if not raw: break
        pages.extend(raw)
        current_start = int(raw[-1][0]) + 3_600_000
        if current_start > end_ms: break
    return _normalize_klines(pages)

def add_custom_indicators(df):
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    
    # Donchian
    df["dh_20"] = df["high"].rolling(20).max().shift(1)
    df["dl_20"] = df["low"].rolling(20).min().shift(1)
    
    # ADX
    adx_ind = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14)
    df["adx"] = adx_ind.adx()
    
    # Bollinger Band Width
    bb_ind = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bbw"] = bb_ind.bollinger_wband()
    
    # ATR Ratio (Current ATR / 100-period SMA of ATR)
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    df["atr_ratio"] = atr / atr.rolling(100).mean()
    
    return df

def run_diagnostic():
    df = fetch_window(ts(2024, 3, 1), ts(2024, 5, 31))
    df = add_custom_indicators(df)
    
    position = None
    entry_price = 0
    target_price = 0
    stop_price = 0
    
    # Feature tracking
    winners = []
    losers = []
    
    for i in range(100, len(df)):
        current = df.iloc[i]
        c, h, l, o = current["close"], current["high"], current["low"], current["open"]
        dh, dl = current["dh_20"], current["dl_20"]
        
        if pd.isna(dh): continue
            
        if position is not None:
            exit_reason = None
            if position == "LONG":
                if o <= stop_price: exit_reason = "SL_GAP"
                elif o > target_price: exit_reason = "TP_GAP"
                elif l <= stop_price: exit_reason = "SL"
                elif h > target_price: exit_reason = "TP"
            else:
                if o >= stop_price: exit_reason = "SL_GAP"
                elif o < target_price: exit_reason = "TP_GAP"
                elif h >= stop_price: exit_reason = "SL"
                elif l < target_price: exit_reason = "TP"
                
            if exit_reason:
                is_win = "TP" in exit_reason
                trade_data = {
                    "adx": entry_adx,
                    "bbw": entry_bbw,
                    "atr_ratio": entry_atr_ratio
                }
                if is_win: winners.append(trade_data)
                else: losers.append(trade_data)
                position = None
                
        if position is None:
            if c > dh:
                position = "LONG"
                entry_price = c
                stop_price = c * (1 - 0.02)
                target_price = c * (1 + 0.05)
                entry_adx = current["adx"]
                entry_bbw = current["bbw"]
                entry_atr_ratio = current["atr_ratio"]
            elif c < dl:
                position = "SHORT"
                entry_price = c
                stop_price = c * (1 + 0.02)
                target_price = c * (1 - 0.05)
                entry_adx = current["adx"]
                entry_bbw = current["bbw"]
                entry_atr_ratio = current["atr_ratio"]

    print("=== March 2024 Genuine Trends vs Whipsaws ===")
    print(f"Total Winners (Genuine Trends): {len(winners)}")
    print(f"Total Losers (Whipsaws/Chop): {len(losers)}\n")
    
    print("AVERAGE METRICS AT TIME OF ENTRY:")
    w_adx = sum(x["adx"] for x in winners)/len(winners) if winners else 0
    l_adx = sum(x["adx"] for x in losers)/len(losers) if losers else 0
    print(f"  ADX 14:           Winners = {w_adx:.1f} | Losers = {l_adx:.1f}")
    
    w_bbw = sum(x["bbw"] for x in winners)/len(winners) if winners else 0
    l_bbw = sum(x["bbw"] for x in losers)/len(losers) if losers else 0
    print(f"  BB Width:         Winners = {w_bbw:.2f} | Losers = {l_bbw:.2f}")
    
    w_atr = sum(x["atr_ratio"] for x in winners)/len(winners) if winners else 0
    l_atr = sum(x["atr_ratio"] for x in losers)/len(losers) if losers else 0
    print(f"  ATR Ratio (100p): Winners = {w_atr:.2f} | Losers = {l_atr:.2f}")

if __name__ == "__main__":
    run_diagnostic()
