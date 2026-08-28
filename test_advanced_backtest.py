from data.binance_api import (
    get_closed_candles
)

from indicators.technical import (
    add_indicators
)

from backtest.engine import (
    run_advanced_backtest
)


symbol = "BTCUSDT"


print(
    "Running Advanced Backtest:",
    symbol
)


df = get_closed_candles(

    symbol,

    interval="1h",

    limit=500

)


df = add_indicators(
    df
)


strategy = {

    "ema_fast":
    20,

    "ema_slow":
    50,

    "sl":
    0.02,

    "tp":
    0.05
}


result = run_advanced_backtest(

    df,

    initial_balance=1000,

    trade_amount=100,

    stop_loss=strategy["sl"],

    take_profit=strategy["tp"],

    fee=0.001,

    strategy=strategy

)


print(
    "\n=============================="
)

print(
    "ADVANCED BACKTEST REPORT"
)

print(
    "=============================="
)


print(
    f"""
Initial:
${result['initial']}

Final:
${result['final']}

Profit:
${result['profit']}

Closed Trades:
{result['trades']}

Wins:
{result['wins']}

Losses:
{result['losses']}

Win Rate:
{result['win_rate']}%

Profit Factor:
{result['profit_factor']}

Sample Quality:
{result['sample_quality']}

Open Position:
{result['open_position']}
"""
)


print(
    "\n=============================="
)

print(
    "EXECUTION HISTORY"
)

print(
    "=============================="
)


for item in result[
    "history"
]:

    print(
        item
    )