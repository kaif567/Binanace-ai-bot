import sys
import json
from verify_donchian_light import ts, fetch_window, WINDOWS, add_indicators, walk_forward_test

df = fetch_window(WINDOWS[0]["start"], WINDOWS[0]["end"])
df = add_indicators(df)
res = walk_forward_test(
    df, 
    initial_train_window=300, 
    test_window=100, 
    step=100, 
    min_oos_trades=1,
    donchian_period=20
)
print(list(res["history"][0].keys()))
