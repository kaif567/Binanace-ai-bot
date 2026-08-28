from data.binance_api import get_candles
from indicators.technical import add_indicators

from backtest.engine import run_advanced_backtest

from backtest.risk import generate_risk_report



symbol="BTCUSDT"



print(
"Running Risk Analysis..."
)



df=get_candles(

    symbol,

    interval="1h",

    limit=1000

)



df=add_indicators(df)



result = run_advanced_backtest(

    df,

    initial_balance=1000,

    trade_amount=100

)



risk = generate_risk_report(

    result["history"]

)



print("\n======================")
print("📊 AI RISK REPORT")
print("======================")



print(

f"""

Maximum Drawdown:
{risk['max_drawdown']}%


Sharpe Ratio:
{risk['sharpe_ratio']}


Volatility:
{risk['volatility']}%


Risk Score:
{risk['risk_score']}/100


Risk Level:
{risk['risk_level']}

"""

)