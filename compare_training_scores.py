"""
Side-by-Side Comparison: Current Training Score vs Proposed Training Score V2

Runs on 1000 real 1h BTCUSDT candles across burn-in windows (100, 200, 300).
Calculates both:
1. Current unmodified calculate_training_score()
2. Proposed calculate_training_score_v2() with n/(n+20) shrinkage

Outputs side-by-side comparison tables.
"""

import math
import urllib.request
import json
import ssl
import certifi
import pandas as pd
from backtest.engine import run_advanced_backtest
from backtest.optimizer import EMA_SETTINGS, STOP_LOSSES, TAKE_PROFITS, prepare_strategy_dataframe, calculate_training_score
from indicators.technical import add_indicators


def calculate_training_score_v2(result):
    """
    Proposed V2 Training Score Formula:
    - 60% weight: Normalized return signal via tanh(avg_return / 0.005)
    - 40% weight: Normalized PF signal via tanh(ln(PF) / ln(2.5))
    - Sample-size shrinkage: n / (n + 20.0) [lower baseline than OOS 50]
    - Returns 0-100 where 50 = neutral
    """
    closed_trades = int(result.get("trades", 0))
    if closed_trades == 0:
        return 0.0

    profit = float(result.get("profit", 0))
    trade_amount = 100.0
    profit_factor = float(result.get("profit_factor", 0))

    # Component 1: Normalized return signal (60%)
    avg_return = (profit / closed_trades) / trade_amount
    return_signal = math.tanh(avg_return / 0.005)

    # Component 2: PF signal (40%)
    if profit_factor > 0:
        pf_signal = math.tanh(math.log(profit_factor) / math.log(2.5))
    else:
        pf_signal = -1.0

    # Weighted edge
    edge = 0.60 * return_signal + 0.40 * pf_signal
    raw_score = 50.0 + 50.0 * edge

    # Confidence shrinkage (n / (n + 20))
    confidence = closed_trades / (closed_trades + 20.0)
    final_score = 50.0 + confidence * (raw_score - 50.0)

    return round(final_score, 2)


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


def run_comparison():
    df = fetch_binance_klines("BTCUSDT", "1h", 1000)
    df = add_indicators(df)

    burn_ins = [100, 200, 300]

    for burn_in in burn_ins:
        train_df = df.iloc[:burn_in].copy().reset_index(drop=True)
        results = []

        for ema_fast, ema_slow in EMA_SETTINGS:
            for sl in STOP_LOSSES:
                for tp in TAKE_PROFITS:
                    strategy = {
                        "ema_fast": ema_fast,
                        "ema_slow": ema_slow,
                        "sl": sl,
                        "tp": tp
                    }
                    temp = prepare_strategy_dataframe(train_df, strategy)
                    result = run_advanced_backtest(
                        temp,
                        initial_balance=1000,
                        trade_amount=100,
                        stop_loss=sl,
                        take_profit=tp,
                        fee=0.001,
                        strategy=strategy,
                        trade_start_index=1,
                        force_close_at_end=True
                    )

                    old_score = calculate_training_score(result)
                    new_score = calculate_training_score_v2(result)

                    results.append({
                        "ema": f"{ema_fast}/{ema_slow}",
                        "sltp": f"{sl:.2f}/{tp:.2f}",
                        "profit": result.get("profit", 0),
                        "pf": result.get("profit_factor", 0),
                        "trades": result.get("trades", 0),
                        "win_rate": result.get("win_rate", 0),
                        "old_score": old_score,
                        "new_score": new_score
                    })

        # Sort by old score
        ranked_old = sorted(results, key=lambda x: x["old_score"], reverse=True)
        # Sort by new score
        ranked_new = sorted(results, key=lambda x: x["new_score"], reverse=True)

        print("\n" + "="*85)
        print(f"BURN-IN WINDOW: {burn_in} CANDLES — ALL 12 CANDIDATE STRATEGIES")
        print("="*85)
        print(f"{'EMA':<10}{'SL/TP':<12}{'Trades':<8}{'Profit':<10}{'PF':<8}{'WinRate':<10}{'Old Score':<12}{'New Score V2':<14}{'Rank (Old->New)'}")
        print("-" * 85)

        for i, item in enumerate(ranked_new, 1):
            # find rank in old list
            old_rank = next(idx for idx, x in enumerate(ranked_old, 1) if x["ema"] == item["ema"] and x["sltp"] == item["sltp"])
            ema = item["ema"]
            sltp = item["sltp"]
            trades = item["trades"]
            profit = f"${item['profit']:.2f}"
            pf = f"{item['pf']:.2f}"
            wr = f"{item['win_rate']:.1f}%"
            old_s = f"{item['old_score']:.2f}"
            new_s = f"{item['new_score']:.2f}"
            rank_shift = f"#{old_rank} -> #{i}"

            print(f"{ema:<10}{sltp:<12}{trades:<8}{profit:<10}{pf:<8}{wr:<10}{old_s:<12}{new_s:<14}{rank_shift}")


if __name__ == "__main__":
    run_comparison()
