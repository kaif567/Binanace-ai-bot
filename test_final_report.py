from data.binance_api import (
    get_closed_candles
)

from indicators.technical import (
    add_indicators
)

from backtest.validation import (
    walk_forward_test
)

from backtest.monte_carlo import (
    monte_carlo_simulation
)

from backtest.risk import (
    generate_risk_report
)

from backtest.report import (
    generate_final_report
)

from backtest.optimizer import (
    prepare_strategy_dataframe
)

from strategy.scoring import (
    calculate_score
)

from database.confidence import (
    get_directional_probability
)


symbol = "BTCUSDT"


print(
    "Generating Separated AI Strategy Report..."
)



df = get_closed_candles(

    symbol,

    interval="1h",

    limit=500

)


df = add_indicators(
    df
)



# =========================
# REAL WALK-FORWARD
# =========================


validation = walk_forward_test(

    df,

    initial_train_window=300,

    test_window=50,

    step=50,

    min_oos_trades=20

)



if validation.get(
    "status"
) != "completed":

    raise AssertionError(
        validation
    )



oos = validation[
    "oos"
]


strategy_params = validation[
    "latest_strategy"
]


strategy_quality = float(
    validation[
        "walk_forward_score"
    ]
)



best = {

    "strategy":
    strategy_params,


    "ema_fast":
    strategy_params.get(
        "ema_fast"
    ),


    "ema_slow":
    strategy_params.get(
        "ema_slow"
    ),


    "sl":
    strategy_params.get(
        "sl"
    ),


    "tp":
    strategy_params.get(
        "tp"
    ),


    "profit":
    oos.get(
        "profit",
        0
    ),


    "trades":
    oos.get(
        "trades",
        0
    ),


    "wins":
    oos.get(
        "wins",
        0
    ),


    "losses":
    oos.get(
        "losses",
        0
    ),


    "win_rate":
    oos.get(
        "win_rate",
        0
    ),


    "profit_factor":
    oos.get(
        "profit_factor",
        0
    ),


    "history":
    oos.get(
        "history",
        []
    ),


    "sample_quality":
    oos.get(
        "sample_quality",
        "LOW_SAMPLE_SIZE"
    ),


    "strategy_quality":
    strategy_quality,


    "walk_forward_score":
    strategy_quality

}



# =========================
# CURRENT SIGNAL
# =========================


signal_df = (
    prepare_strategy_dataframe(
        df,
        strategy_params
    )
)


market = calculate_score(

    signal_df,

    best

)


direction = market.get(
    "direction",
    "FLAT"
)


signal_strength = float(
    market.get(
        "signal_strength",
        0
    )
)



# =========================
# HISTORICAL PROBABILITY
# =========================


probability = (
    get_directional_probability(
        direction
    )
)



directional_probability = (
    probability.get(
        "directional_probability"
    )
)


probability_sample = int(
    probability.get(
        "sample",
        0
    )
)



# =========================
# MONTE CARLO
# =========================


monte = monte_carlo_simulation(

    best[
        "history"
    ],

    simulations=1000

)



# =========================
# RISK
# =========================


risk = generate_risk_report(

    best,

    monte

)



# =========================
# FACTUAL FINAL REPORT
# =========================


report = generate_final_report(

    best,

    validation,

    monte,

    risk,

    strategy_quality=
    strategy_quality,

    signal_strength=
    signal_strength,

    direction=
    direction,

    directional_probability=
    directional_probability,

    directional_probability_sample=
    probability_sample,

    paper_status=
    "TEST_MODE",

    paper_eligible=
    False

)



if "confidence" in report:

    raise AssertionError(
        "Final report still contains generic confidence"
    )



required_report_keys = [

    "strategy_quality",

    "signal_strength",

    "direction",

    "directional_probability",

    "directional_probability_sample",

    "risk_level",

    "summary"

]


for key in required_report_keys:


    if key not in report:

        raise AssertionError(
            f"Missing report key: {key}"
        )



required_risk_keys = [

    "max_drawdown",

    "sharpe_ratio",

    "volatility",

    "risk_level",

    "status"

]


for key in required_risk_keys:


    if key not in risk:

        raise AssertionError(
            f"Missing risk key: {key}"
        )



print(
    "\n=============================="
)

print(
    "🏆 FINAL SEPARATED REPORT"
)

print(
    "=============================="
)


print(
    "Strategy Quality:",
    report[
        "strategy_quality"
    ]
)


print(
    "Signal Strength:",
    report[
        "signal_strength"
    ]
)


print(
    "Direction:",
    report[
        "direction"
    ]
)


print(
    "Directional Probability:",
    report[
        "directional_probability"
    ]
)


print(
    "Probability Sample:",
    report[
        "directional_probability_sample"
    ]
)


print(
    "\nOOS Profit:",
    report[
        "summary"
    ][
        "oos_profit"
    ]
)


print(
    "OOS Trades:",
    report[
        "summary"
    ][
        "oos_trades"
    ]
)


print(
    "OOS Win Rate:",
    report[
        "summary"
    ][
        "oos_win_rate"
    ]
)


print(
    "OOS Profit Factor:",
    report[
        "summary"
    ][
        "oos_profit_factor"
    ]
)


print(
    "\nMonte Carlo Probability:",
    report[
        "profit_probability"
    ]
)


print(
    "\nMax Drawdown:",
    risk[
        "max_drawdown"
    ],
    "%"
)


print(
    "Sharpe Ratio:",
    risk[
        "sharpe_ratio"
    ]
)


print(
    "Volatility:",
    risk[
        "volatility"
    ],
    "%"
)


print(
    "Risk Score:",
    risk[
        "risk_score"
    ]
)


print(
    "Risk Level:",
    risk[
        "risk_level"
    ]
)


print(
    "\nFINAL REPORT REGRESSION TEST: PASS ✅"
)