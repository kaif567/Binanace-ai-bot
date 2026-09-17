import math
import urllib.request
import json
import ssl
import certifi
import pandas as pd
from backtest.engine import run_advanced_backtest
from indicators.technical import add_indicators
from backtest.optimizer import prepare_strategy_dataframe
from indicators.mtf import get_4h_trend_from_df

def fetch_binance_klines_from_timestamp(symbol, interval, start_ts, limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_ts}&limit={limit}"
    context = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=context, timeout=15) as response:
        data = json.loads(response.read().decode())

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
        
    return df

def run_mtf_comparison():
    print("Fetching 1h historical data for comparison...")
    # Jan 2024 to test
    df_1h = fetch_binance_klines_from_timestamp("BTCUSDT", "1h", 1704067200000, 2000)
    df_1h = add_indicators(df_1h)
    
    print("Fetching 4h historical data for comparison...")
    df_4h = fetch_binance_klines_from_timestamp("BTCUSDT", "4h", 1704067200000, 500)
    df_4h = add_indicators(df_4h)
    
    # We will use a standard baseline strategy
    strategy = {'ema_fast': 30, 'ema_slow': 100, 'sl': 0.02, 'tp': 0.08}
    df_1h = prepare_strategy_dataframe(df_1h, strategy)
    
    print("Running Baseline (No MTF Filter)...")
    res_baseline = run_advanced_backtest(
        df_1h.copy(),
        initial_balance=1000,
        trade_amount=100,
        stop_loss=strategy["sl"],
        take_profit=strategy["tp"],
        strategy=strategy,
        mtf_df=None
    )
    
    print("Running Filtered (With MTF Filter)...")
    res_filtered = run_advanced_backtest(
        df_1h.copy(),
        initial_balance=1000,
        trade_amount=100,
        stop_loss=strategy["sl"],
        take_profit=strategy["tp"],
        strategy=strategy,
        mtf_df=df_4h
    )
    
    print("\n--- MTF CONFLUENCE RESULTS COMPARISON ---")
    print(f"{'Metric':<20} | {'Baseline':<15} | {'With 4h MTF'}")
    print("-" * 55)
    print(f"{'Total Trades':<20} | {res_baseline.get('trades'):<15} | {res_filtered.get('trades')}")
    print(f"{'Total Profit ($)':<20} | {res_baseline.get('profit'):<15.2f} | {res_filtered.get('profit'):.2f}")
    print(f"{'Win Rate (%)':<20} | {res_baseline.get('win_rate'):<15.1f} | {res_filtered.get('win_rate'):.1f}")
    print(f"{'Profit Factor':<20} | {res_baseline.get('profit_factor'):<15.2f} | {res_filtered.get('profit_factor'):.2f}")
    print("-" * 55)
    
if __name__ == "__main__":
    run_mtf_comparison()

