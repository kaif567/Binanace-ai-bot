from data.binance_api import (
    get_closed_candles
)

from indicators.technical import (
    add_indicators
)

from strategy.scoring import (
    calculate_score
)


symbol = "BTCUSDT"


print(
    "Analyzing Closed-Candle Score:",
    symbol
)


df = get_closed_candles(

    symbol,

    interval="1h",

    limit=100

)


df = add_indicators(
    df
)


result = calculate_score(
    df
)



required_keys = [

    "market_score",

    "signal",

    "direction",

    "signal_strength",

    "reasons"

]


for key in required_keys:


    if key not in result:

        raise AssertionError(
            f"Missing scoring key: {key}"
        )



if "confidence" in result:

    raise AssertionError(
        "Scoring still exposes generic confidence"
    )



print(
    "\n===================="
)

print(
    "AI MARKET SCORE"
)

print(
    "===================="
)


print(
    "Market Score:",
    result[
        "market_score"
    ],
    "/100"
)


print(
    "Signal:",
    result[
        "signal"
    ]
)


print(
    "Direction:",
    result[
        "direction"
    ]
)


print(
    "Signal Strength:",
    result[
        "signal_strength"
    ],
    "/100"
)


print(
    "\nReasons:"
)


for reason in result[
    "reasons"
]:

    print(
        "✓",
        reason
    )


print(
    "\nSCORING REGRESSION TEST: PASS ✅"
)