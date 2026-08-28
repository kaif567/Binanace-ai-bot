from backtest.validation import (
    walk_forward_test
)


def improve_strategy(
    df,
    initial_train_window=300,
    test_window=50,
    step=50,
    min_oos_trades=20,
    initial_balance=1000,
    trade_amount=100,
    fee=0.001
):
    """
    REAL self optimizer.

    Old behavior removed:
    - no random parameter mutation
    - no artificial +5 score
    - no fake improvement

    Strategy quality now comes only from
    walk-forward OOS performance.
    """

    print(
        "\n🧠 REAL SELF OPTIMIZER STARTED"
    )

    validation = walk_forward_test(
        df,

        initial_train_window=
        initial_train_window,

        test_window=
        test_window,

        step=
        step,

        min_oos_trades=
        min_oos_trades,

        initial_balance=
        initial_balance,

        trade_amount=
        trade_amount,

        fee=
        fee
    )

    if validation.get(
        "status"
    ) != "completed":

        return {
            "status":
            "failed",

            "message":
            validation.get(
                "message",
                "Walk-forward optimization failed"
            ),

            "strategy":
            {},

            "score":
            0,

            "walk_forward":
            validation
        }

    strategy = dict(
        validation.get(
            "latest_strategy",
            {}
        )
    )

    oos = validation.get(
        "oos",
        {}
    )

    score = float(
        oos.get(
            "walk_forward_score",
            0
        )
    )

    print(
        "\n🏆 WALK-FORWARD STRATEGY"
    )

    print(
        strategy
    )

    print(
        "OOS Score:",
        score
    )

    print(
        "OOS Sample Quality:",
        oos.get(
            "sample_quality"
        )
    )

    return {
        "status":
        "completed",

        "strategy":
        strategy,

        "score":
        score,

        "walk_forward_score":
        score,

        "oos":
        oos,

        "walk_forward":
        validation
    }