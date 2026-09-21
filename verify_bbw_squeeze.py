import sys
import os
import pandas as pd
import ta
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines

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
        raw = _fetch_klines_page(symbol="BTCUSDT", interval="1h", limit=1000, start_time=current_start, end_time=end_ms)
        if not raw: break
        pages.extend(raw)
        current_start = int(raw[-1][0]) + 3_600_000
        if current_start > end_ms: break
    return _normalize_klines(pages)

def format_row(window, run_label, trades, wr, pf, robustness, drop_top_2):
    return f"| {window:<9} | {run_label:<19} | {trades:<6} | {wr:<5.2f} | {pf:<5.2f} | {robustness:<11} | {drop_top_2:<13.2f} |"

def format_time(ts_ms):
    return datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%00')

def add_custom_indicators(df):
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    
    # Donchian
    df["dh_20"] = df["high"].rolling(20).max().shift(1)
    df["dl_20"] = df["low"].rolling(20).min().shift(1)
    
    # Bollinger Band Width
    bb_ind = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bbw"] = bb_ind.bollinger_wband()
    
    return df

def backtest_bbw(df, donchian_period=20, bbw_threshold=4.0, trade_amount=100, fee=0.001):
    history = []
    position = None
    entry_price = 0
    stop_price = 0
    target_price = 0
    entry_time = 0
    
    for i in range(100, len(df)):
        current = df.iloc[i]
        c, h, l, o = current["close"], current["high"], current["low"], current["open"]
        dh, dl = current["dh_20"], current["dl_20"]
        bbw = current["bbw"]
        
        if pd.isna(dh): continue
            
        if position is not None:
            exit_reason = None
            if position == "LONG":
                if o <= stop_price: exit_reason = "SL_GAP"; exit_price_actual = o
                elif o > target_price: exit_reason = "TP_GAP"; exit_price_actual = o
                elif l <= stop_price: exit_reason = "SL"; exit_price_actual = stop_price
                elif h > target_price: exit_reason = "TP"; exit_price_actual = target_price
            else:
                if o >= stop_price: exit_reason = "SL_GAP"; exit_price_actual = o
                elif o < target_price: exit_reason = "TP_GAP"; exit_price_actual = o
                elif h >= stop_price: exit_reason = "SL"; exit_price_actual = stop_price
                elif l < target_price: exit_reason = "TP"; exit_price_actual = target_price
                
            if exit_reason:
                if position == "LONG": gross_return = (exit_price_actual - entry_price) / entry_price
                else: gross_return = (entry_price - exit_price_actual) / entry_price
                
                gross_profit = trade_amount * gross_return
                net_profit = gross_profit - (trade_amount * fee * 2)
                
                history.append({
                    "position": position, "entry_price": entry_price, "exit_price": exit_price_actual,
                    "gross_profit": gross_profit, "profit": net_profit, "exit_reason": exit_reason
                })
                position = None
                
        if position is None:
            if c > dh and bbw < bbw_threshold:
                position = "LONG"
                entry_price = c; stop_price = c*0.98; target_price = c*1.05
            elif c < dl and bbw < bbw_threshold:
                position = "SHORT"
                entry_price = c; stop_price = c*1.02; target_price = c*0.95
                
    if position is not None:
        last = df.iloc[-1]
        exit_price_actual = float(last["close"])
        if position == "LONG": gross_return = (exit_price_actual - entry_price) / entry_price
        else: gross_return = (entry_price - exit_price_actual) / entry_price
        gross_profit = trade_amount * gross_return
        net_profit = gross_profit - (trade_amount * fee * 2)
        history.append({
            "position": position, "entry_price": entry_price, "exit_price": exit_price_actual,
            "gross_profit": gross_profit, "profit": net_profit, "exit_reason": "FORCE_CLOSE"
        })
        
    return history

def run_tests():
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    
    table_lines = []
    table_lines.append("| Window    | Run                 | Trades | WR    | PF    | Robustness  | PF drop top-2 |")
    table_lines.append("|-----------|---------------------|--------|-------|-------|-------------|---------------|")

    for w in WINDOWS:
        sys.stderr.write(f"Fetching {w['name']}...\n")
        df = fetch_window(w["start"], w["end"])
        if df is None or len(df) == 0: continue
        df = add_custom_indicators(df)
        
        sys.stderr.write(f"  Running BBW Squeeze for {w['name']}...\n")
        history = backtest_bbw(df, bbw_threshold=4.0)
        
        trades = len(history)
        if trades < 3:
            table_lines.append(format_row(w["name"], "BBW < 4.0", trades, 0, 0, "FAILED", 0))
            continue
            
        win_trades = len([t for t in history if t["profit"] > 0])
        wr = (win_trades / trades) * 100
        
        gross_profit = sum(t["gross_profit"] for t in history if t["profit"] > 0)
        gross_loss = abs(sum(t["profit"] for t in history if t["profit"] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        winners = sorted([t for t in history if t["profit"] > 0], key=lambda x: x["profit"], reverse=True)
        if len(winners) >= 2:
            top_2_profit = winners[0]["profit"] + winners[1]["profit"]
            ex_profit = gross_profit - top_2_profit
            ex_pf = ex_profit / gross_loss if gross_loss > 0 else 0
        else:
            ex_pf = pf
            
        if pf < 1.0: robustness = "FAILED"
        elif ex_pf >= 1.0: robustness = "ROBUST"
        else: robustness = "FRAGILE"
            
        table_lines.append(format_row(w["name"], "BBW < 4.0", trades, wr, pf, robustness, ex_pf))
    
    sys.stdout.close()
    sys.stdout = original_stdout
    
    print("\n\n" + "="*77)
    for line in table_lines:
        print(line)
    print("="*77 + "\n")

if __name__ == "__main__":
    run_tests()
