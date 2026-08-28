from data.binance_api import (
    get_closed_candles
)

from indicators.technical import (
    add_indicators
)

from backtest.pipeline import (
    run_ai_pipeline
)


symbol = "BTCUSDT"


print(
    """
============================
🤖 ITEM 6 PIPELINE TEST
============================
"""
)


df = get_closed_candles(

    symbol,

    interval="1h",

    limit=500

)


df = add_indicators(
    df
)


result = run_ai_pipeline(

    df,

    symbol=symbol,

    initial_train_window=300,

    test_window=50,

    step=50,

    min_oos_trades=20

)



required_keys = [

    "strategy_quality",

    "market_score",

    "signal_strength",

    "direction",

    "directional_probability",

    "directional_probability_sample",

    "paper_eligible",

    "paper_mode"

]


for key in required_keys:


    if key not in result:

        raise AssertionError(
            f"Missing pipeline key: {key}"
        )



if "confidence" in result:

    raise AssertionError(
        "Legacy generic confidence still exists"
    )



print(
    """
============================
🏆 SEPARATED PIPELINE RESULT
============================
"""
)


print(
    "Best Strategy:"
)

print(
    result[
        "best_strategy"
    ]
)


print(
    "\nStrategy Quality:",
    result[
        "strategy_quality"
    ]
)


print(
    "Market Score:",
    result[
        "market_score"
    ]
)


print(
    "Signal Strength:",
    result[
        "signal_strength"
    ]
)


print(
    "Direction:",
    result[
        "direction"
    ]
)


print(
    "Directional Probability:",
    result[
        "directional_probability"
    ]
)


print(
    "Probability Sample:",
    result[
        "directional_probability_sample"
    ]
)


print(
    "Probability Status:",
    result[
        "probability_status"
    ]
)


print(
    "Paper Mode:",
    result[
        "paper_mode"
    ]
)


print(
    "Paper Eligible:",
    result[
        "paper_eligible"
    ]
)


print(
    "OOS Sample Quality:",
    result[
        "validation"
    ][
        "sample_quality"
    ]
)


print(
    "\nPIPELINE REGRESSION TEST: PASS ✅"
)