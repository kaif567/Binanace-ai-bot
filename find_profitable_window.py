"""
Find Historical Window with Profitable Strategy Candidates

Scans multiple date ranges to find periods where EMA strategies generated profit.
"""

import urllib.request
import json
import ssl
import certifi
import pandas as pd
from backtest.engine import run_advanced_backtest
from backtest.optimizer import EMA_SETTINGS, STOP_LOSSES, TAKE_PROFITS, prepare_strategy_dataframe
from indicators.technical import add_indicators


def fetch_binance_klines_from_timestamp(symbol, interval, start_ts, limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_ts}&limit={limit}"
    context = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=context, timeout=15) as response:
        data = json.loads(response.read().decode())

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df[["open", "high", "low", "close", "volume"]]


def test_window_profitability(df, window_label):
    df = add_indicators(df)

    profitable_count = 0
    for ema_fast, ema_slow in EMA_SETTINGS:
        for sl in STOP_LOSSES:
            for tp in TAKE_PROFITS:
                strategy = {"ema_fast": ema_fast, "ema_slow": ema_slow, "sl": sl, "tp": tp}
                temp = prepare_strategy_dataframe(df, strategy)
                result = run_advanced_backtest(
                    temp, initial_balance=1000, trade_amount=100,
                    stop_loss=sl, take_profit=tp, fee=0.001,
                    strategy=strategy, trade_start_index=1, force_close_at_end=True
                )

                if result.get("profit", 0) > 0 and result.get("profit_factor", 0) > 1.0:
                    profitable_count += 1

    return profitable_count


if __name__ == "__main__":
    periods = [
        ("2024-01 (bull run)", 1704067200000),
        ("2024-03 (Q1 volatility)", 1709251200000),
        ("2023-11 (pre-halving)", 1698796800000),
        ("2023-01 (recovery)", 1672531200000),
        ("2021-09 (alt season)", 1630454400000),
    ]

    print("="*70)
    print("SCANNING HISTORICAL WINDOWS FOR PROFITABLE STRATEGIES")
    print("="*70)

    for label, start_ts in periods:
        print(f"\n{label}...")
        try:
            df = fetch_binance_klines_from_timestamp("BTCUSDT", "1h", start_ts, 1000)
            start_price = df['close'].iloc[0]
            end_price = df['close'].iloc[-1]
            pct_change = ((end_price - start_price) / start_price) * 100

            profitable = test_window_profitability(df.iloc[:300].copy(), label)

            print(f"  Price: ${start_price:.0f} -> ${end_price:.0f} ({pct_change:+.1f}%)")
            print(f"  Profitable candidates (first 300 candles): {profitable}/12")

            if profitable >= 3:
                print(f"  ✓ VIABLE WINDOW (≥3 profitable candidates)")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
