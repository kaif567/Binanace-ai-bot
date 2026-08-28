import time

from data.binance_api import get_candles
from indicators.technical import add_indicators
from strategy.scoring import calculate_score



COINS = [

    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT"

]



def scan_market():


    results = []


    for coin in COINS:


        try:

            df = get_candles(
                coin,
                interval="1h",
                limit=100
            )


            df = add_indicators(df)


            analysis = calculate_score(df)


            results.append({

                "coin": coin,

                "score": analysis["score"],

                "signal": analysis["signal"],

                "confidence": analysis["confidence"]

            })


        except Exception as e:

            print(
                coin,
                "Error:",
                e
            )


    return results





def print_scanner(results):


    print("\n")
    print("="*45)
    print("🚀 BINANCE AI MARKET SCANNER")
    print("="*45)



    sorted_results = sorted(
        results,
        key=lambda x:x["score"],
        reverse=True
    )


    for item in sorted_results:


        print(
        f"""
{item['coin']}

Score:
{item['score']}/100

Signal:
{item['signal']}

Confidence:
{item['confidence']}%

--------------------
"""
        )
