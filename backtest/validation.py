from backtest.engine import (
    run_advanced_backtest
)

from backtest.optimizer import (
    advanced_optimizer,
    calculate_strategy_score,
    prepare_strategy_dataframe
)


def _aggregate_oos_history(
    folds,
    min_oos_trades
):
    """
    Combine ONLY unseen test-fold trades.

    Training trades never enter these metrics.
    """

    history = []

    for fold in folds:
        fold_number = fold[
            "fold"
        ]

        testing_history = (
            fold[
                "testing"
            ].get(
                "history",
                []
            )
        )

        for item in testing_history:
            copied = dict(
                item
            )

            copied[
                "walk_forward_fold"
            ] = fold_number

            history.append(
                copied
            )

    closed_trades = [
        item
        for item in history
        if item.get(
            "type"
        ) in [
            "SELL",
            "COVER"
        ]
    ]

    profits = [
        float(
            item.get(
                "profit",
                0
            )
        )
        for item in closed_trades
    ]

    wins = len([
        value
        for value in profits
        if value > 0
    ])

    losses = (
        len(profits)
        -
        wins
    )

    total = len(
        profits
    )

    total_profit = sum(
        profits
    )

    gross_profit = sum(
        value
        for value in profits
        if value > 0
    )

    gross_loss = abs(
        sum(
            value
            for value in profits
            if value < 0
        )
    )

    if total > 0:
        win_rate = (
            wins
            /
            total
        ) * 100
    else:
        win_rate = 0.0

    if gross_loss > 0:
        profit_factor = (
            gross_profit
            /
            gross_loss
        )

    elif gross_profit > 0:
        profit_factor = (
            gross_profit
        )

    else:
        profit_factor = 0.0

    if total >= min_oos_trades:
        sample_quality = (
            "OOS_SUFFICIENT"
        )

    else:
        sample_quality = (
            "LOW_SAMPLE_SIZE"
        )

    metrics = {
        "profit":
        round(
            total_profit,
            8
        ),

        "trades":
        total,

        "wins":
        wins,

        "losses":
        losses,

        "win_rate":
        round(
            win_rate,
            2
        ),

        "profit_factor":
        round(
            profit_factor,
            4
        ),

        "history":
        history,

        "sample_quality":
        sample_quality
    }

    metrics[
        "walk_forward_score"
    ] = calculate_strategy_score(
        metrics
    )

    return metrics


def walk_forward_test(
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
    REAL expanding-window walk-forward test.

    Testing defaults:
        300 train
        50 test
        50 step

    Later live research can use:
        1500 train
        200 test
        200 step

    Example 500 rows:

    Fold 1:
    Train 0..299
    Test  300..349

    Fold 2:
    Train 0..349
    Test  350..399

    Fold 3:
    Train 0..399
    Test  400..449

    Fold 4:
    Train 0..449
    Test  450..499
    """

    print(
        "\n📈 REAL WALK-FORWARD VALIDATION"
    )

    if (
        df is None
        or
        len(df) == 0
    ):
        return {
            "status": "failed",
            "message": "Empty dataframe",
            "folds": []
        }

    initial_train_window = int(
        initial_train_window
    )

    test_window = int(
        test_window
    )

    step = int(
        step
    )

    min_oos_trades = int(
        min_oos_trades
    )

    if initial_train_window < 3:
        raise ValueError(
            "initial_train_window must be at least 3"
        )

    if test_window <= 0:
        raise ValueError(
            "test_window must be greater than 0"
        )

    if step <= 0:
        raise ValueError(
            "step must be greater than 0"
        )

    # Prevent double-counting overlapping OOS
    # candles/trades during aggregate scoring.
    if step < test_window:
        raise ValueError(
            "step must be >= test_window "
            "to avoid overlapping OOS folds"
        )

    minimum_required = (
        initial_train_window
        +
        test_window
    )

    if len(df) < minimum_required:
        return {
            "status": "failed",

            "message": (
                "Not enough candles for walk-forward. "
                f"Need at least {minimum_required}, "
                f"received {len(df)}."
            ),

            "folds": [],

            "initial_train_window":
            initial_train_window,

            "test_window":
            test_window,

            "step":
            step
        }

    folds = []

    latest_training_ranked = []

    latest_strategy = None

    train_end = (
        initial_train_window
    )

    fold_number = 1

    while True:
        test_start = (
            train_end
        )

        test_end = (
            test_start
            +
            test_window
        )

        # Only complete OOS test windows.
        if test_end > len(df):
            break

        # ==================================
        # TRAINING DATA ONLY
        # ==================================

        train_df = (
            df.iloc[
                :train_end
            ]
            .copy()
            .reset_index(
                drop=True
            )
        )

        print(
            f"\n--- WALK-FORWARD FOLD {fold_number} ---"
        )

        print(
            "Train:",
            0,
            "to",
            train_end - 1,
            "| Test:",
            test_start,
            "to",
            test_end - 1
        )

        training_ranked = (
            advanced_optimizer(
                train_df,

                initial_balance=
                initial_balance,

                trade_amount=
                trade_amount,

                fee=fee,

                force_close_at_end=True
            )
        )

        if not training_ranked:
            return {
                "status": "failed",

                "message": (
                    "Optimizer failed on "
                    f"fold {fold_number}"
                ),

                "folds":
                folds
            }

        training_best = (
            training_ranked[0]
        )

        selected_strategy = dict(
            training_best[
                "strategy"
            ]
        )

        # ==================================
        # OOS TEST PREFIX
        # ==================================
        #
        # We include historical rows before
        # test_start only for indicator context.
        #
        # Engine trading is BLOCKED until
        # trade_start_index.
        #
        # No candle after test_end is visible.

        evaluation_prefix = (
            df.iloc[
                :test_end
            ]
            .copy()
            .reset_index(
                drop=True
            )
        )

        evaluation_prefix = (
            prepare_strategy_dataframe(
                evaluation_prefix,
                selected_strategy
            )
        )

        testing_result = (
            run_advanced_backtest(
                evaluation_prefix,

                initial_balance=
                initial_balance,

                trade_amount=
                trade_amount,

                stop_loss=float(
                    selected_strategy[
                        "sl"
                    ]
                ),

                take_profit=float(
                    selected_strategy[
                        "tp"
                    ]
                ),

                fee=fee,

                strategy=
                selected_strategy,

                trade_start_index=
                test_start,

                # Boundary solution:
                # close remaining open trade
                # at final OOS candle CLOSE.
                force_close_at_end=True
            )
        )

        folds.append({
            "fold":
            fold_number,

            "train_start":
            0,

            "train_end":
            train_end - 1,

            "train_size":
            train_end,

            "test_start":
            test_start,

            "test_end":
            test_end - 1,

            "test_size":
            test_window,

            "selected_strategy":
            selected_strategy,

            "training": {
                "profit":
                training_best.get(
                    "profit",
                    0
                ),

                "trades":
                training_best.get(
                    "trades",
                    0
                ),

                "win_rate":
                training_best.get(
                    "win_rate",
                    0
                ),

                "profit_factor":
                training_best.get(
                    "profit_factor",
                    0
                ),

                "training_score":
                training_best.get(
                    "training_score",
                    training_best.get(
                        "score",
                        0
                    )
                )
            },

            "testing":
            testing_result
        })

        latest_strategy = (
            selected_strategy
        )

        latest_training_ranked = (
            training_ranked
        )

        fold_number += 1

        train_end += step

    if not folds:
        return {
            "status": "failed",
            "message":
            "No full walk-forward folds produced",
            "folds": []
        }

    # ==================================
    # AGGREGATE ONLY OOS RESULTS
    # ==================================

    oos = _aggregate_oos_history(
        folds,
        min_oos_trades
    )

    print(
        "\n===== WALK-FORWARD OOS SUMMARY ====="
    )

    print(
        "Folds:",
        len(folds)
    )

    print(
        "OOS Profit:",
        oos["profit"]
    )

    print(
        "OOS Trades:",
        oos["trades"]
    )

    print(
        "OOS Win Rate:",
        oos["win_rate"]
    )

    print(
        "OOS Profit Factor:",
        oos["profit_factor"]
    )

    print(
        "OOS Score:",
        oos[
            "walk_forward_score"
        ]
    )

    print(
        "Sample Quality:",
        oos[
            "sample_quality"
        ]
    )

    return {
        "status":
        "completed",

        "mode":
        "EXPANDING_WINDOW",

        "boundary_rule":
        "MARK_TO_MARKET",

        "initial_train_window":
        initial_train_window,

        "test_window":
        test_window,

        "step":
        step,

        "min_oos_trades":
        min_oos_trades,

        "fold_count":
        len(folds),

        "folds":
        folds,

        "latest_strategy":
        latest_strategy,

        "latest_training_ranked":
        latest_training_ranked,

        "oos":
        oos,

        # compatibility / direct access
        "profit":
        oos["profit"],

        "trades":
        oos["trades"],

        "wins":
        oos["wins"],

        "losses":
        oos["losses"],

        "win_rate":
        oos["win_rate"],

        "profit_factor":
        oos["profit_factor"],

        "history":
        oos["history"],

        "sample_quality":
        oos["sample_quality"],

        "walk_forward_score":
        oos[
            "walk_forward_score"
        ]
    }