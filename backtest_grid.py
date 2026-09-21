import pandas as pd
import numpy as np
import requests
import datetime
import time

def fetch_klines(symbol, start_ts, end_ts):
    all_data = []
    current_start = start_ts
    while current_start < end_ts:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=1000&startTime={current_start}&endTime={end_ts}"
        res = requests.get(url)
        data = res.json()
        if not data or not isinstance(data, list): break
        all_data.extend(data)
        current_start = data[-1][0] + 15 * 60 * 1000
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbv', 'tbqav', 'ignore']
    df = pd.DataFrame(all_data, columns=cols)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    return df.drop_duplicates('open_time').sort_values('open_time').reset_index(drop=True)

def ts(y, m, d):
    return int(datetime.datetime(y, m, d, tzinfo=datetime.timezone.utc).timestamp() * 1000)

def run_grid_backtest(df, start_idx, name):
    # Setup Range using past 90 days (from start_idx back)
    # 90 days = 90 * 24 * 4 = 8640 15m candles
    history = df.iloc[max(0, start_idx-8640):start_idx]
    lower_bound = history['low'].min()
    upper_bound = history['high'].max()
    
    spacing = 0.015 # 1.5%
    levels = []
    p = lower_bound
    while p <= upper_bound:
        levels.append({"price": p, "has_inv": False, "base": 0.0})
        p *= (1 + spacing)
        
    capital = 1000.0
    fiat = capital
    crypto = 0.0
    alloc = capital / len(levels)
    fee = 0.001
    
    stop_loss_price = lower_bound * 0.95 # 5% below grid
    
    print(f"\n[{name}]")
    print(f"Range: {lower_bound:.2f} - {upper_bound:.2f} | Levels: {len(levels)} | SL: {stop_loss_price:.2f}")
    
    test_df = df.iloc[start_idx:].copy()
    last_price = test_df.iloc[0]['open']
    
    trades = 0
    sl_hit = False
    
    for i, row in test_df.iterrows():
        curr = row['close']
        high = row['high']
        low = row['low']
        
        # Check Stop Loss
        if low <= stop_loss_price:
            if crypto > 0:
                fiat += (crypto * stop_loss_price) * (1 - fee)
                crypto = 0.0
                for lvl in levels: lvl["has_inv"] = False
                sl_hit = True
                print(f"🚨 STOP LOSS HIT at {stop_loss_price:.2f} on {row['open_time']}")
            break # Stop trading for this window
            
        # Check Sells (Price went up)
        # Assuming intra-candle high hits our sell limit
        for j in range(len(levels) - 1):
            if levels[j]["has_inv"] and high >= levels[j+1]["price"]:
                base = levels[j]["base"]
                val = base * levels[j+1]["price"]
                fiat += val * (1 - fee)
                crypto -= base
                levels[j]["has_inv"] = False
                levels[j]["base"] = 0.0
                trades += 1
                
        # Check Buys (Price went down)
        for j in range(len(levels)):
            if not levels[j]["has_inv"] and low <= levels[j]["price"]:
                if fiat >= alloc:
                    base = alloc / levels[j]["price"]
                    net_base = base * (1 - fee)
                    fiat -= alloc
                    crypto += net_base
                    levels[j]["has_inv"] = True
                    levels[j]["base"] = net_base
                    trades += 1

    final_price = test_df.iloc[-1]['close'] if not sl_hit else stop_loss_price
    final_val = fiat + (crypto * final_price)
    roi = (final_val - capital) / capital * 100
    bh_roi = (final_price - test_df.iloc[0]['open']) / test_df.iloc[0]['open'] * 100
    
    print(f"Trades: {trades} | Final Val: ${final_val:.2f} | Grid ROI: {roi:.2f}% | Buy&Hold ROI: {bh_roi:.2f}%")
    return roi

# Fetch 2023-Oct to 2024-Aug data (to allow 90-day history for Jan 2024 start)
df = fetch_klines("BTCUSDT", ts(2023, 10, 1), ts(2024, 8, 31))

# Window 1: Jan-Mar (Bull)
idx_jan = df[df['open_time'] >= '2024-01-01'].index[0]
idx_apr = df[df['open_time'] >= '2024-04-01'].index[0]
run_grid_backtest(df.iloc[:idx_apr], idx_jan, "W1: Jan-Mar (Bull Breakout)")

# Window 2: Apr-May (Correction)
idx_jun = df[df['open_time'] >= '2024-06-01'].index[0]
run_grid_backtest(df.iloc[:idx_jun], idx_apr, "W2: Apr-May (Correction/Chop)")

# Window 3: Jun-Aug (Summer Chop)
idx_sep = len(df) - 1
run_grid_backtest(df.iloc[:idx_sep], idx_jun, "W3: Jun-Aug (Summer Chop)")

