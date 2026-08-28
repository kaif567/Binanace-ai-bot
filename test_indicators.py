from data.binance_api import get_candles
from indicators.technical import add_indicators, get_trend


symbol = "BTCUSDT"


print("Analyzing:", symbol)


df = get_candles(
    symbol,
    interval="1h",
    limit=100
)


df = add_indicators(df)


trend = get_trend(df)


last = df.iloc[-1]


print("\n===== TECHNICAL ANALYSIS =====")


print(
f"""
Price:
${last.close}

RSI:
{round(last.rsi,2)}

EMA20:
{round(last.ema20,2)}

EMA50:
{round(last.ema50,2)}

MACD:
{round(last.macd,4)}

Trend:
{trend}
"""
)