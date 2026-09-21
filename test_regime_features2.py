import sys
from test_regime_features import fetch_window, add_custom_indicators, ts
import pandas as pd

WINDOWS = [
    {"name": "Aug 2023", "start": ts(2023, 8, 1), "end": ts(2023, 10, 31)},
    {"name": "Jan 2024", "start": ts(2024, 1, 1), "end": ts(2024, 3, 31)},
    {"name": "Mar 2024", "start": ts(2024, 3, 1), "end": ts(2024, 5, 31)},
    {"name": "Jun 2024", "start": ts(2024, 6, 1), "end": ts(2024, 8, 31)}
]

def run_diagnostic():
    for w in WINDOWS:
        df = fetch_window(w["start"], w["end"])
        df = add_custom_indicators(df)
        
        position = None
        entry_price = 0
        target_price = 0
        stop_price = 0
        
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
                    trade_data = {"adx": entry_adx, "bbw": entry_bbw, "atr_ratio": entry_atr_ratio}
                    if is_win: winners.append(trade_data)
                    else: losers.append(trade_data)
                    position = None
                    
            if position is None:
                if c > dh:
                    position = "LONG"
                    entry_price = c; stop_price = c*0.98; target_price = c*1.05
                    entry_adx = current["adx"]; entry_bbw = current["bbw"]; entry_atr_ratio = current["atr_ratio"]
                elif c < dl:
                    position = "SHORT"
                    entry_price = c; stop_price = c*1.02; target_price = c*0.95
                    entry_adx = current["adx"]; entry_bbw = current["bbw"]; entry_atr_ratio = current["atr_ratio"]

        print(f"=== {w['name']} ===")
        w_adx = sum(x["adx"] for x in winners)/len(winners) if winners else 0
        l_adx = sum(x["adx"] for x in losers)/len(losers) if losers else 0
        w_bbw = sum(x["bbw"] for x in winners)/len(winners) if winners else 0
        l_bbw = sum(x["bbw"] for x in losers)/len(losers) if losers else 0
        print(f"  ADX 14:  Win = {w_adx:.1f} | Loss = {l_adx:.1f}")
        print(f"  BBW:     Win = {w_bbw:.2f} | Loss = {l_bbw:.2f}")

if __name__ == "__main__":
    run_diagnostic()
