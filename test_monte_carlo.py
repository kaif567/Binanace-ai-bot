from data.binance_api import get_candles
from indicators.technical import add_indicators

from backtest.engine import run_advanced_backtest

from backtest.monte_carlo import monte_carlo_simulation



symbol="BTCUSDT"



print(
    "Running Monte Carlo Simulation..."
)



df=get_candles(

    symbol,

    interval="1h",

    limit=1000

)



df=add_indicators(df)



# Run strategy first

result = run_advanced_backtest(

    df,

    initial_balance=1000,

    trade_amount=100

)



simulation = monte_carlo_simulation(

    result["history"],

    simulations=1000

)



print("\n============================")
print("🎲 MONTE CARLO REPORT")
print("============================")



print(

f"""

Simulations:
{simulation['simulations']}


Average Ending Balance:
${simulation['average']}


Best Case:
${simulation['best_case']}


Worst Case:
${simulation['worst_case']}


Median:
${simulation['median']}


Probability of Profit:
{simulation['profit_probability']}%

"""

)