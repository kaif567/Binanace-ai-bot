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
    "Running Professional Backtest:",
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


result = run_advanced_backtest(

    df,

    initial_balance=1000,

    trade_amount=100,

    stop_loss=0.02,

    take_profit=0.05,

    fee=0.001

)


print(
    "\n=========================="
)

print(
    "PROFESSIONAL BACKTEST"
)

print(
    "=========================="
)


print(
    f"""
Starting Capital:
${result['initial']}

Final Capital:
${result['final']}

Profit/Loss:
${result['profit']}

Closed Trades:
{result['trades']}

Winning Trades:
{result['wins']}

Losing Trades:
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
    "\nRecent Execution History:"
)


for trade in result[
    "history"
][-10:]:

    print(
        trade
    )