import sys
import os
import pandas as pd
from datetime import datetime, timezone
from data.binance_api import _fetch_klines_page, _normalize_klines
from indicators.technical import add_indicators

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

def backtest_trailing_atr(df, donchian_period=20, atr_mult=3.5, trade_amount=100, fee=0.001):
    history = []
    position = None
    entry_price = 0
    stop_price = 0
    entry_time = 0
    
    # We iterate starting from donchian_period
    for i in range(len(df)):
        current = df.iloc[i]
        close = float(current["close"])
        high = float(current["high"])
        low = float(current["low"])
        candle_open = float(current["open"])
        atr = float(current.get("atr", 0))
        dh = float(current.get(f"donchian_high_{donchian_period}", 0))
        dl = float(current.get(f"donchian_low_{donchian_period}", 0))
        
        if pd.isna(dh) or pd.isna(dl) or atr == 0 or pd.isna(atr):
            continue
            
        if position is not None:
            # Check exit
            exit_reason = None
            exit_price_actual = None
            
            if position == "LONG":
                # Adverse gap
                if candle_open <= stop_price:
                    exit_price_actual = candle_open
                    exit_reason = "TRAILING_STOP_GAP"
                elif low <= stop_price:
                    exit_price_actual = stop_price
                    exit_reason = "TRAILING_STOP"
                    
                if exit_reason:
                    gross_return = (exit_price_actual - entry_price) / entry_price
                else:
                    # Update trailing stop based on close (or high? usually close)
                    new_stop = close - (atr_mult * atr)
                    if new_stop > stop_price:
                        stop_price = new_stop
            
            elif position == "SHORT":
                # Adverse gap
                if candle_open >= stop_price:
                    exit_price_actual = candle_open
                    exit_reason = "TRAILING_STOP_GAP"
                elif high >= stop_price:
                    exit_price_actual = stop_price
                    exit_reason = "TRAILING_STOP"
                    
                if exit_reason:
                    gross_return = (entry_price - exit_price_actual) / entry_price
                else:
                    # Update trailing stop based on close
                    new_stop = close + (atr_mult * atr)
                    if new_stop < stop_price:
                        stop_price = new_stop
                        
            if exit_reason:
                gross_profit = trade_amount * gross_return
                entry_fee = trade_amount * fee
                exit_fee = trade_amount * fee
                net_profit = gross_profit - entry_fee - exit_fee
                
                history.append({
                    "position": position,
                    "entry_price": entry_price,
                    "exit_price": exit_price_actual,
                    "gross_profit": gross_profit,
                    "profit": net_profit,
                    "exit_reason": exit_reason,
                    "entry_time": entry_time,
                    "exit_time": int(current["time"])
                })
                position = None
                
        # Only check entry if not in position
        if position is None:
            if close > dh:
                position = "LONG"
                entry_price = close
                stop_price = close - (atr_mult * atr)
                entry_time = int(current["time"])
            elif close < dl:
                position = "SHORT"
                entry_price = close
                stop_price = close + (atr_mult * atr)
                entry_time = int(current["time"])
                
    # Force close end
    if position is not None:
        last = df.iloc[-1]
        exit_price_actual = float(last["close"])
        if position == "LONG":
            gross_return = (exit_price_actual - entry_price) / entry_price
        else:
            gross_return = (entry_price - exit_price_actual) / entry_price
            
        gross_profit = trade_amount * gross_return
        net_profit = gross_profit - (trade_amount * fee * 2)
        history.append({
            "position": position,
            "entry_price": entry_price,
            "exit_price": exit_price_actual,
            "gross_profit": gross_profit,
            "profit": net_profit,
            "exit_reason": "FORCE_CLOSE",
            "entry_time": entry_time,
            "exit_time": int(last["time"])
        })
        
    return history

def run_tests():
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    
    table_lines = []
    table_lines.append("| Window    | Run                 | Trades | WR    | PF    | Robustness  | PF drop top-2 |")
    table_lines.append("|-----------|---------------------|--------|-------|-------|-------------|---------------|")

    histories = {}

    for w in WINDOWS:
        sys.stderr.write(f"Fetching {w['name']}...\n")
        df = fetch_window(w["start"], w["end"])
        if df is None or len(df) == 0: continue
        df = add_indicators(df)
        
        sys.stderr.write(f"  Running Trailing ATR for {w['name']}...\n")
        history = backtest_trailing_atr(df, donchian_period=20, atr_mult=3.5)
        histories[w['name']] = history
        
        trades = len(history)
        if trades < 3:
            table_lines.append(format_row(w["name"], "Trailing ATR 3.5", trades, 0, 0, "FAILED", 0))
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
            
        table_lines.append(format_row(w["name"], "Trailing ATR 3.5", trades, wr, pf, robustness, ex_pf))
    
    sys.stdout.close()
    sys.stdout = original_stdout
    
    print("\n\n" + "="*77)
    for line in table_lines:
        print(line)
    print("="*77 + "\n")

if __name__ == "__main__":
    run_tests()
