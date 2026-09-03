"""
Baseline Burn-In Instability Diagnostic Test (Verified SSL with Certifi CA Bundle)

Fetches real BTCUSDT 15m candle data from Binance public API
Runs advanced_optimizer() across burn-in windows: 100, 200, 300 candles.
Observes:
1. Top candidate selection across burn-ins (does it flip between EMA 10/50 and 30/100?)
2. Score compression / saturation / near-ties (do multiple candidates get 90+ / 100 scores?)
3. Score spread between rank 1 and rank 2 candidates
"""

import urllib.request
import json
import ssl
import certifi
import pandas as pd
from backtest.optimizer import advanced_optimizer
from indicators.technical import add_indicators


def fetch_binance_klines(symbol="BTCUSDT", interval="1h", limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
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


def run_burnin_test():
    print("="*70)
    print("FETCHING 1000 BTCUSDT 1h CANDLES (VERIFIED SSL via certifi CA)...")
    print("="*70)

    df = fetch_binance_klines("BTCUSDT", "1h", 1000)
    print(f"Successfully fetched {len(df)} real BTCUSDT 1h candles.")
    print(f"Start Price: ${df['close'].iloc[0]:.2f} | End Price: ${df['close'].iloc[-1]:.2f}")

    # Add RSI, MACD, and all other indicators (production requirement)
    df = add_indicators(df)
    print("Indicators added (RSI, MACD, EMA20, EMA50, BB, ATR, ADX, volume_avg).")

    burn_ins = [100, 200, 300]
    results_by_burnin = {}

    print("\n" + "="*70)
    print("RUNNING OPTIMIZER WITH CURRENT UNMODIFIED calculate_training_score()")
    print("="*70)

    for burn_in in burn_ins:
        train_df = df.iloc[:burn_in].copy().reset_index(drop=True)
        ranked = advanced_optimizer(
            train_df,
            initial_balance=1000,
            trade_amount=100,
            fee=0.001,
            force_close_at_end=True
        )
        results_by_burnin[burn_in] = ranked

        print(f"\n{'='*25} BURN-IN: {burn_in} CANDLES {'='*25}")
        print(f"Total candidate parameter sets tested: {len(ranked)}")
        print("\nTOP 5 CANDIDATES:")
        print(f"{'Rank':<5}{'EMA':<12}{'SL/TP':<12}{'Score':<10}{'Profit':<10}{'PF':<10}{'Trades':<8}{'WinRate':<8}")
        print("-" * 75)
        for i, cand in enumerate(ranked[:5], 1):
            ema = f"{cand['ema_fast']}/{cand['ema_slow']}"
            sltp = f"{cand['sl']}/{cand['tp']}"
            score = cand['training_score']
            profit = f"${cand['profit']:.2f}"
            pf = f"{cand['profit_factor']:.2f}"
            trades = cand['trades']
            wr = f"{cand['win_rate']:.1f}%"
            print(f"{i:<5}{ema:<12}{sltp:<12}{score:<10}{profit:<10}{pf:<10}{trades:<8}{wr:<8}")

        top_score = ranked[0]['training_score']
        near_ties = [c for c in ranked if top_score - c['training_score'] <= 5.0 and top_score > 0]
        print(f"\nCandidates within 5.0 pts of Rank 1 (Score: {top_score}): {len(near_ties)} / {len(ranked)}")
        if len(ranked) >= 2 and top_score > 0:
            gap = top_score - ranked[1]['training_score']
            print(f"Gap between Rank 1 and Rank 2: {gap:.2f} pts")

    print("\n" + "="*70)
    print("CROSS-BURN-IN STABILITY COMPARISON")
    print("="*70)
    print(f"{'Burn-In':<10}{'Rank 1 EMA':<15}{'Rank 1 SL/TP':<15}{'Score':<10}{'Profit':<10}{'PF':<8}{'Trades':<8}")
    print("-" * 76)
    for burn_in in burn_ins:
        top = results_by_burnin[burn_in][0]
        ema = f"{top['ema_fast']}/{top['ema_slow']}"
        sltp = f"{top['sl']}/{top['tp']}"
        print(f"{burn_in:<10}{ema:<15}{sltp:<15}{top['training_score']:<10}${top['profit']:<9.2f}{top['profit_factor']:<8.2f}{top['trades']:<8}")


if __name__ == "__main__":
    run_burnin_test()
