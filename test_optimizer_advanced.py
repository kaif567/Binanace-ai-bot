from data.binance_api import (
    get_closed_candles
)

from indicators.technical import (
    add_indicators
)

from backtest.optimizer import (
    advanced_optimizer
)


symbol = "BTCUSDT"


print(
    "Running Advanced Training Optimizer..."
)


df = get_closed_candles(
    symbol,
    interval="1h",
    limit=500
)

df = add_indicators(
    df
)


results = advanced_optimizer(
    df
)


print(
    "\n=========================="
)

print(
    "🏆 ADVANCED OPTIMIZER RESULTS"
)

print(
    "=========================="
)


for i, item in enumerate(
    results[:10],
    1
):
    strategy = item[
        "strategy"
    ]

    print(
        f"""
Rank:
{i}

EMA:
{strategy['ema_fast']}/{strategy['ema_slow']}

Stop Loss:
{strategy['sl'] * 100}%

Take Profit:
{strategy['tp'] * 100}%

Profit:
${item['profit']}

Trades:
{item['trades']}

Win Rate:
{item['win_rate']}%

Profit Factor:
{item['profit_factor']}

Training Score:
{item['training_score']}

Sample Quality:
{item['sample_quality']}

--------------------
"""
    )