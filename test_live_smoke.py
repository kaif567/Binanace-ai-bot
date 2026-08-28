from database import paper_store

from monitor.paper_trader import (
    check_open_position
)

from monitor.live_monitor import (
    handle_paper_entry
)

from data.binance_api import (
    get_price,
    get_latest_closed_candle,
    get_closed_candles_paginated
)

from indicators.technical import (
    add_indicators
)

from backtest.pipeline import (
    run_ai_pipeline
)


SYMBOL = "BTCUSDT"

HISTORICAL_CANDLES = 3000

INITIAL_TRAIN_WINDOW = 1500

TEST_WINDOW = 200

STEP = 200

MIN_OOS_TRADES = 20


def expect(
        condition,
        message
):

    if not condition:

        raise AssertionError(
            message
        )


def main():

    print(
        "======================================"
    )

    print(
        "FULL LIVE SMOKE TEST"
    )

    print(
        "======================================"
    )


    # ==============================
    # PAPER STATE
    # ==============================

    trades_before = (
        paper_store.load_trades()
    )


    blocking_position = (
        check_open_position()
    )


    expect(

        blocking_position
        is None,

        (
            "Blocking paper position still exists. "
            "Resolve legacy/stale position before "
            "live smoke testing."
        )

    )


    print(
        "PAPER STATE: PASS ✅"
    )


    # ==============================
    # LIVE PRICE
    # ==============================

    current_price = float(
        get_price(
            SYMBOL
        )
    )


    expect(
        current_price > 0,
        "Invalid Binance live price"
    )


    print(
        "Live Price:",
        current_price
    )


    print(
        "LIVE TICKER: PASS ✅"
    )


    # ==============================
    # LIGHT POLL
    # ==============================

    latest = (
        get_latest_closed_candle(

            SYMBOL,

            interval="1h"

        )
    )


    expect(
        latest is not None,
        "Light Poll returned no closed candle"
    )


    latest_closed_time = int(
        latest[
            "time"
        ]
    )


    print(
        "Latest Closed Candle:",
        latest_closed_time
    )


    print(
        "LIGHT POLL: PASS ✅"
    )


    # ==============================
    # HEAVY FETCH
    # ==============================

    df, integrity = (
        get_closed_candles_paginated(

            SYMBOL,

            interval="1h",

            limit=
            HISTORICAL_CANDLES,

            recent_gap_window_candles=
            24,

            truncate_historical_gaps=
            True,

            return_report=
            True

        )
    )


    expect(

        len(
            df
        )
        >=
        (
            INITIAL_TRAIN_WINDOW
            +
            TEST_WINDOW
        ),

        (
            "Continuous history is too short "
            "for 1500/200 walk-forward."
        )

    )


    expect(

        df[
            "time"
        ].is_unique,

        "Heavy dataset contains duplicate timestamps"

    )


    expect(

        df[
            "time"
        ].is_monotonic_increasing,

        "Heavy dataset is not chronological"

    )


    expect(

        integrity.get(
            "recent_gap_count",
            0
        )
        ==
        0,

        (
            "Recent historical gap detected. "
            "Smoke test fails closed."
        )

    )


    heavy_latest_time = int(
        df.iloc[
            -1
        ][
            "time"
        ]
    )


    expect(

        heavy_latest_time
        >=
        latest_closed_time,

        (
            "Heavy dataset does not contain "
            "the latest Light Poll candle."
        )

    )


    print(
        "Requested:",
        HISTORICAL_CANDLES
    )


    print(
        "Received:",
        len(
            df
        )
    )


    print(
        "Pages:",
        integrity.get(
            "pages"
        )
    )


    print(
        "Duplicates Removed:",
        integrity.get(
            "pagination_duplicates_removed"
        )
    )


    print(
        "Historical Gaps:",
        integrity.get(
            "historical_gap_count"
        )
    )


    print(
        "Recent Gaps:",
        integrity.get(
            "recent_gap_count"
        )
    )


    print(
        "HEAVY PAGINATION: PASS ✅"
    )


    # ==============================
    # INDICATORS
    # ==============================

    df = (
        add_indicators(
            df
        )
    )


    required_indicator_columns = [

        "ema20",

        "ema50",

        "rsi",

        "macd",

        "atr",

        "adx"

    ]


    for column in required_indicator_columns:

        expect(

            column
            in
            df.columns,

            (
                "Missing indicator column: "
                +
                column
            )

        )


    print(
        "INDICATORS: PASS ✅"
    )


    # ==============================
    # REAL WALK-FORWARD PIPELINE
    # ==============================

    result = (
        run_ai_pipeline(

            df,

            symbol=
            SYMBOL,

            initial_train_window=
            INITIAL_TRAIN_WINDOW,

            test_window=
            TEST_WINDOW,

            step=
            STEP,

            min_oos_trades=
            MIN_OOS_TRADES

        )
    )


    required_pipeline_keys = [

        "best_strategy",

        "strategy_quality",

        "market_signal",

        "market_score",

        "signal_strength",

        "direction",

        "directional_probability",

        "directional_probability_sample",

        "paper_eligible",

        "paper_mode"

    ]


    for key in required_pipeline_keys:

        expect(

            key
            in
            result,

            (
                "Pipeline missing key: "
                +
                key
            )

        )


    expect(

        "confidence"
        not in
        result,

        (
            "Legacy generic confidence "
            "returned by pipeline"
        )

    )


    print(
        "\n=============================="
    )

    print(
        "REAL PIPELINE RESULT"
    )

    print(
        "=============================="
    )


    print(
        "Strategy Quality:",
        result[
            "strategy_quality"
        ]
    )


    print(
        "Market Signal:",
        result[
            "market_signal"
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
        "\nWALK-FORWARD PIPELINE: PASS ✅"
    )


    # ==============================
    # DETERMINISTIC KILL-SWITCH TEST
    # ==============================
    #
    # We deliberately pass an eligible
    # synthetic paper setup here.
    #
    # paper_entries_enabled=False MUST
    # suppress it before execute_paper_trade
    # can create any position.

    paper_count_before = len(
        paper_store.load_trades()
    )


    suppression = (
        handle_paper_entry(

            symbol=
            SYMBOL,


            direction=
            "UP",


            paper_eligible=
            True,


            paper_reason=
            "",


            strategy=
            result.get(
                "best_strategy",
                {}
            ),


            strategy_quality=
            100.0,


            signal_strength=
            100.0,


            directional_probability=
            100.0,


            probability_sample=
            100,


            current_price=
            current_price,


            signal_atr=
            float(
                df.iloc[
                    -1
                ][
                    "atr"
                ]
            ),


            paper_entries_enabled=
            False

        )
    )


    expect(

        suppression.get(
            "event"
        )
        ==
        "SUPPRESSED",

        (
            "Paper kill switch did not "
            "suppress eligible entry."
        )

    )


    paper_count_after = len(
        paper_store.load_trades()
    )


    expect(

        paper_count_after
        ==
        paper_count_before,

        (
            "Smoke test unexpectedly created "
            "a paper trade."
        )

    )


    print(
        "PAPER ENTRY SUPPRESSED: PASS ✅"
    )


    # ==============================
    # ORIGINAL PAPER STATE PRESERVED
    # ==============================

    trades_after = (
        paper_store.load_trades()
    )


    expect(

        len(
            trades_after
        )
        ==
        len(
            trades_before
        ),

        (
            "Smoke test changed paper-trade "
            "record count."
        )

    )


    print(
        "PAPER TRADE FILE PRESERVED: PASS ✅"
    )


    print(
        "\n======================================"
    )

    print(
        "FULL LIVE SMOKE TEST: PASS ✅"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    main()