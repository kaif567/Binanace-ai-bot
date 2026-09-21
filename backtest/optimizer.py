import math

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


def calculate_training_score(
    result
):
    """
    Score used only for selecting a strategy
    INSIDE the training window.

    V2 Normalized Training Score:
    - Component 1 (60%): Normalized return signal via tanh(avg_return / 0.005)
    - Component 2 (40%): Normalized PF signal via tanh(ln(PF) / ln(2.5))
    - Sample-size shrinkage: n / (n + 20.0) [lower baseline than OOS 50]
    - Returns 0-100 where 50 = neutral / no statistical edge

    Final strategy quality comes from OOS walk-forward results
    via calculate_oos_strategy_quality().
    """

    closed_trades = int(
        result.get(
            "trades",
            0
        )
    )

    if closed_trades == 0:
        return 0.0

    profit = float(
        result.get(
            "profit",
            0
        )
    )

    trade_amount = 100.0

    profit_factor = float(
        result.get(
            "profit_factor",
            0
        )
    )

    # Component 1: Normalized return signal (60% weight)
    avg_return = (
        (profit / closed_trades)
        /
        trade_amount
    )

    return_signal = math.tanh(
        avg_return / 0.005
    )

    # Component 2: Normalized profit factor signal (40% weight)
    if profit_factor > 0:
        pf_signal = math.tanh(
            math.log(profit_factor)
            /
            math.log(2.5)
        )
    else:
        pf_signal = -1.0

    # Weighted edge
    edge = (
        0.60 * return_signal
        +
        0.40 * pf_signal
    )

    raw_score = (
        50.0 + 50.0 * edge
    )

    # Training window confidence shrinkage (n / (n + 20.0))
    confidence = (
        closed_trades
        /
        (closed_trades + 20.0)
    )

    final_score = (
        50.0
        +
        confidence * (raw_score - 50.0)
    )

    return round(
        final_score,
        2
    )


# Backwards-compatibility alias
calculate_strategy_score = calculate_training_score


def calculate_oos_strategy_quality(
    result
):
    """
    V2 Strategy Quality formula for OOS results only.

    Component 1 (60%): Normalized return signal via tanh
    Component 2 (40%): Profit factor signal via tanh
    Sample-size shrinkage: n/(n+50)

    Returns score 0-100 where:
        50 = neutral/no-edge
        <50 = negative evidence
        >50 = positive evidence
    """

    closed_trades = int(
        result.get(
            "trades",
            0
        )
    )

    if closed_trades == 0:
        return 0.0

    profit = float(
        result.get(
            "profit",
            0
        )
    )

    trade_amount = 100.0

    profit_factor = float(
        result.get(
            "profit_factor",
            0
        )
    )

    # Component 1: Normalized return signal (60% weight)
    avg_return = (
        (profit / closed_trades)
        /
        trade_amount
    )

    return_signal = math.tanh(
        avg_return / 0.005
    )

    # Component 2: PF signal (40% weight)
    if profit_factor > 0:
        pf_signal = math.tanh(
            math.log(profit_factor)
            /
            math.log(2.5)
        )
    else:
        pf_signal = -1.0

    # Weighted edge
    edge = (
        0.60 * return_signal
        +
        0.40 * pf_signal
    )

    # Raw score (before shrinkage)
    raw_score = 50.0 + 50.0 * edge

    # Sample-size shrinkage
    confidence = (
        closed_trades
        /
        (closed_trades + 50.0)
    )

    final_score = (
        50.0
        +
        confidence * (raw_score - 50.0)
    )

    return round(
        final_score,
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
    donchian_period=20,
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
                    
                    donchian_period=donchian_period,

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