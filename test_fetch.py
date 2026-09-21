import sys
from verify_trailing_atr import fetch_window, WINDOWS
for w in WINDOWS:
    df = fetch_window(w["start"], w["end"])
    print(w["name"], len(df) if df is not None else "None")
