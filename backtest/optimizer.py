from backtest.engine import (
    run_advanced_backtest
)


EMA_SETTINGS = [
    (10, 50),
    (20, 50),
    (30, 100)
]

STOP_LOSSES = [
    0.01,
    0.02
]

TAKE_PROFITS = [
    0.05,
    0.08
]


def calculate_strategy_score(
    result
):
    """
    Score used only for selecting a strategy
    INSIDE the training window.

    Final strategy quality will come from OOS
    walk-forward results instead.
    """

    profit = float(
        result.get(
            "profit",
            0
        )
    )

    win_rate = float(
        result.get(
            "win_rate",
            0
        )
    )

    profit_factor = float(
        result.get(
            "profit_factor",
            0
        )
    )

    trades = int(
        result.get(
            "trades",
            0
        )
    )

    score = 0.0

    if profit > 0:
        score += min(
            profit * 5,
            40
        )

    score += min(
        win_rate * 0.4,
        30
    )

    score += min(
        profit_factor * 15,
        20
    )

    if trades >= 10:
        score += 10

    return round(
        min(
            score,
            100
        ),
        2
    )


def prepare_strategy_dataframe(
    df,
    strategy
):
    """
    Calculate the EMA pair required by a
    particular candidate strategy.

    Pandas EWM is causal: each row only uses
    current and previous rows.
    """

    data = df.copy()

    ema_fast = int(
        strategy.get(
            "ema_fast",
            20
        )
    )

    ema_slow = int(
        strategy.get(
            "ema_slow",
            50
        )
    )

    data[
        f"ema{ema_fast}"
    ] = (
        data["close"]
        .ewm(
            span=ema_fast,
            adjust=False
        )
        .mean()
    )

    data[
        f"ema{ema_slow}"
    ] = (
        data["close"]
        .ewm(
            span=ema_slow,
            adjust=False
        )
        .mean()
    )

    return data


def advanced_optimizer(
    df,
    initial_balance=1000,
    trade_amount=100,
    fee=0.001,
    force_close_at_end=True
):
    """
    TRAINING-ONLY optimizer.

    IMPORTANT:
    Do not pass future/OOS candles here.

    Walk-forward validation is responsible
    for supplying only the training slice.
    """

    if (
        df is None
        or
        len(df) < 3
    ):
        return []

    results = []

    for ema_fast, ema_slow in EMA_SETTINGS:

        for sl in STOP_LOSSES:

            for tp in TAKE_PROFITS:
                strategy = {
                    "ema_fast":
                    ema_fast,

                    "ema_slow":
                    ema_slow,

                    "sl":
                    sl,

                    "tp":
                    tp
                }

                temp = (
                    prepare_strategy_dataframe(
                        df,
                        strategy
                    )
                )

                result = run_advanced_backtest(
                    temp,

                    initial_balance=
                    initial_balance,

                    trade_amount=
                    trade_amount,

                    stop_loss=sl,

                    take_profit=tp,

                    fee=fee,

                    strategy=strategy,

                    trade_start_index=1,

                    force_close_at_end=
                    force_close_at_end
                )

                score = (
                    calculate_strategy_score(
                        result
                    )
                )

                results.append({
                    "strategy":
                    strategy,

                    "ema_fast":
                    ema_fast,

                    "ema_slow":
                    ema_slow,

                    "sl":
                    sl,

                    "tp":
                    tp,

                    "profit":
                    result.get(
                        "profit",
                        0
                    ),

                    "win_rate":
                    result.get(
                        "win_rate",
                        0
                    ),

                    "profit_factor":
                    result.get(
                        "profit_factor",
                        0
                    ),

                    "trades":
                    result.get(
                        "trades",
                        0
                    ),

                    "history":
                    result.get(
                        "history",
                        []
                    ),

                    "sample_quality":
                    result.get(
                        "sample_quality",
                        "LOW_SAMPLE_SIZE"
                    ),

                    "training_score":
                    score,

                    # compatibility keys
                    "ai_score":
                    score,

                    "score":
                    score
                })

    results.sort(
        key=lambda item:
        item.get(
            "training_score",
            0
        ),
        reverse=True
    )

    print(
        "\n===== TRAINING OPTIMIZER TOP ====="
    )

    for item in results[:3]:
        print(
            "Score:",
            item.get(
                "training_score"
            ),
            "| Profit:",
            item.get(
                "profit"
            ),
            "| Win Rate:",
            item.get(
                "win_rate"
            )
        )

    return results