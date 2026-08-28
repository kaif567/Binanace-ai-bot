import json
import os
import tempfile

import pandas as pd


from database import paper_store

from database import performance

import data.binance_api as binance_api

import monitor.paper_trader as paper_trader


ONE_MINUTE_MS = (
    60
    *
    1000
)


ONE_HOUR_MS = (
    60
    *
    60
    *
    1000
)


ORIGINAL_TRADE_FILE = (
    paper_store.TRADE_FILE
)


ORIGINAL_RANGE_FETCH = (
    binance_api.get_closed_candles_range
)


ORIGINAL_PAGE_FETCH = (
    binance_api._fetch_klines_page
)


ORIGINAL_SERVER_TIME = (
    binance_api.get_server_time
)


def expect(
        condition,
        message
):

    if not condition:

        raise AssertionError(
            message
        )


def eligible_data(
        direction="UP",
        price=100.0,
        atr=1.0
):

    return {

        "symbol":
        "BTCUSDT",


        "direction":
        direction,


        "strategy_quality":
        80.0,


        "signal_strength":
        70.0,


        "directional_probability":
        None,


        "directional_probability_sample":
        0,


        "best_strategy":
        {

            "ema_fast":
            20,


            "ema_slow":
            50

        },


        "price":
        price,


        "atr":
        atr

    }


def reset_state():

    paper_store.save_trades_atomic(
        []
    )


def open_position(
        direction="UP"
):

    trade = (
        paper_trader.execute_paper_trade(

            eligible_data(
                direction=direction
            )

        )
    )


    expect(

        trade.get(
            "status"
        )
        ==
        "OPEN",

        trade

    )


    return trade


def make_recovery_df(
        candles
):

    return pd.DataFrame(
        candles
    )


# ==============================
# PERSISTENCE
# ==============================

def test_persistent_state():

    reset_state()


    trade = (
        open_position(
            "UP"
        )
    )


    position_id = (
        trade[
            "position_id"
        ]
    )


    loaded = (
        paper_store.load_trades()
    )


    expect(

        len(
            loaded
        )
        ==
        1,

        loaded

    )


    expect(

        loaded[
            0
        ][
            "position_id"
        ]
        ==
        position_id,

        loaded

    )


    expect(

        loaded[
            0
        ][
            "side"
        ]
        ==
        "LONG",

        loaded

    )


    expect(

        abs(
            float(
                loaded[
                    0
                ][
                    "entry_fee"
                ]
            )
            -
            0.1
        )
        <
        1e-10,

        loaded

    )


    with open(

        paper_store.TRADE_FILE,

        "r",

        encoding="utf-8"

    ) as file:

        parsed = (
            json.load(
                file
            )
        )


    expect(

        isinstance(
            parsed,
            list
        ),

        parsed

    )


    print(
        "OPEN POSITION PERSISTENCE: PASS ✅"
    )


    print(
        "ATOMIC JSON STATE: PASS ✅"
    )


# ==============================
# CORRUPT STATE
# ==============================

def test_corrupt_state_fails_closed():

    with open(

        paper_store.TRADE_FILE,

        "w",

        encoding="utf-8"

    ) as file:

        file.write(
            "{ invalid json"
        )


    failed = False


    try:

        paper_store.load_trades()


    except paper_store.PaperStateError:

        failed = True


    expect(

        failed,

        "Corrupt state did not fail closed"

    )


    reset_state()


    print(
        "CORRUPT STATE FAIL-CLOSED: PASS ✅"
    )


# ==============================
# LONG TP
# ==============================

def test_long_tp_exact():

    reset_state()


    position = (
        open_position(
            "UP"
        )
    )


    tp = float(
        position[
            "take_profit_price"
        ]
    )


    now_ms = (

        int(
            position[
                "last_checked_time_ms"
            ]
        )

        +

        10_000

    )


    result = (
        paper_trader.manage_open_position(

            current_price=
            tp
            +
            10,

            now_ms=
            now_ms

        )
    )


    expect(

        result[
            "event"
        ]
        ==
        "CLOSED",

        result

    )


    closed = (
        result[
            "position"
        ]
    )


    expect(

        closed[
            "exit_reason"
        ]
        ==
        "TAKE_PROFIT",

        closed

    )


    expect(

        abs(
            float(
                closed[
                    "exit_price"
                ]
            )
            -
            tp
        )
        <
        1e-8,

        closed

    )


    print(
        "LONG TP EXACT LIMIT FILL: PASS ✅"
    )


# ==============================
# LONG SL
# ==============================

def test_long_slippage():

    reset_state()


    position = (
        open_position(
            "UP"
        )
    )


    sl = float(
        position[
            "stop_loss_price"
        ]
    )


    now_ms = (

        int(
            position[
                "last_checked_time_ms"
            ]
        )

        +

        10_000

    )


    result = (
        paper_trader.manage_open_position(

            current_price=
            sl,

            now_ms=
            now_ms

        )
    )


    expected_exit = (

        sl

        *

        (
            1
            -
            paper_trader.STOP_SLIPPAGE_RATE
        )

    )


    closed = (
        result[
            "position"
        ]
    )


    expect(

        closed[
            "exit_reason"
        ]
        ==
        "STOP_LOSS",

        closed

    )


    expect(

        abs(
            float(
                closed[
                    "exit_price"
                ]
            )
            -
            expected_exit
        )
        <
        1e-6,

        closed

    )


    print(
        "LONG SL MARKET SLIPPAGE: PASS ✅"
    )


# ==============================
# LONG ADVERSE GAP
# ==============================

def test_long_adverse_gap():

    reset_state()


    position = (
        open_position(
            "UP"
        )
    )


    now_ms = (

        int(
            position[
                "last_checked_time_ms"
            ]
        )

        +

        10_000

    )


    result = (
        paper_trader.manage_open_position(

            current_price=
            95.0,

            now_ms=
            now_ms

        )
    )


    expected = (

        95.0

        *

        (
            1
            -
            paper_trader.STOP_SLIPPAGE_RATE
        )

    )


    expect(

        result[
            "event"
        ]
        ==
        "CLOSED",

        result

    )


    expect(

        abs(
            float(
                result[
                    "position"
                ][
                    "exit_price"
                ]
            )
            -
            expected
        )
        <
        1e-6,

        result

    )


    print(
        "LONG ADVERSE GAP + SLIPPAGE: PASS ✅"
    )


# ==============================
# SHORT TP + PNL
# ==============================

def test_short_tp_and_math():

    reset_state()


    position = (
        open_position(
            "DOWN"
        )
    )


    expect(

        position[
            "side"
        ]
        ==
        "SHORT",

        position

    )


    tp = float(
        position[
            "take_profit_price"
        ]
    )


    entry = float(
        position[
            "entry_price"
        ]
    )


    now_ms = (

        int(
            position[
                "last_checked_time_ms"
            ]
        )

        +

        10_000

    )


    result = (
        paper_trader.manage_open_position(

            current_price=
            tp
            -
            5,

            now_ms=
            now_ms

        )
    )


    expect(

        result[
            "event"
        ]
        ==
        "CLOSED",

        result

    )


    closed = (
        result[
            "position"
        ]
    )


    expected_gross_percent = (

        (
            entry
            -
            tp
        )

        /

        entry

        *

        100

    )


    expected_net_percent = (

        expected_gross_percent

        -

        (
            paper_trader.FEE_RATE
            *
            2
            *
            100
        )

    )


    expect(

        closed[
            "side"
        ]
        ==
        "SHORT",

        closed

    )


    expect(

        abs(
            float(
                closed[
                    "exit_price"
                ]
            )
            -
            tp
        )
        <
        1e-8,

        closed

    )


    expect(

        abs(
            float(
                closed[
                    "gross_return"
                ]
            )
            -
            expected_gross_percent
        )
        <
        1e-6,

        closed

    )


    expect(

        abs(
            float(
                closed[
                    "return"
                ]
            )
            -
            expected_net_percent
        )
        <
        1e-6,

        closed

    )


    expect(

        abs(
            float(
                closed[
                    "fee_cost"
                ]
            )
            -
            0.20
        )
        <
        1e-8,

        closed

    )


    print(
        "SHORT TP EXACT FILL: PASS ✅"
    )


    print(
        "SHORT PNL FORMULA: PASS ✅"
    )


    print(
        "ROUND-TRIP FEES 0.20%: PASS ✅"
    )


# ==============================
# SHORT SL
# ==============================

def test_short_slippage():

    reset_state()


    position = (
        open_position(
            "DOWN"
        )
    )


    sl = float(
        position[
            "stop_loss_price"
        ]
    )


    now_ms = (

        int(
            position[
                "last_checked_time_ms"
            ]
        )

        +

        10_000

    )


    result = (
        paper_trader.manage_open_position(

            current_price=
            sl,

            now_ms=
            now_ms

        )
    )


    expected = (

        sl

        *

        (
            1
            +
            paper_trader.STOP_SLIPPAGE_RATE
        )

    )


    expect(

        result[
            "event"
        ]
        ==
        "CLOSED",

        result

    )


    expect(

        abs(
            float(
                result[
                    "position"
                ][
                    "exit_price"
                ]
            )
            -
            expected
        )
        <
        1e-6,

        result

    )


    print(
        "SHORT SL MARKET SLIPPAGE: PASS ✅"
    )


# ==============================
# RECOVERY THRESHOLD
# ==============================

def test_recovery_thresholds():

    reset_state()


    position = (
        open_position(
            "UP"
        )
    )


    original_last = int(
        position[
            "last_checked_time_ms"
        ]
    )


    calls = {
        "count":
        0
    }


    def fake_range(
            *args,
            **kwargs
    ):

        calls[
            "count"
        ] += 1


        return pd.DataFrame(

            columns=[

                "time",

                "open",

                "high",

                "low",

                "close",

                "volume",

                "close_time"

            ]

        )


    previous_range_fetch = (
        binance_api.get_closed_candles_range
    )


    try:

        binance_api.get_closed_candles_range = (
            fake_range
        )


        # =========================
        # 90 SEC
        # =========================

        result = (
            paper_trader.manage_open_position(

                current_price=
                100.0,

                now_ms=
                original_last
                +
                90_000

            )
        )


        expect(

            calls[
                "count"
            ]
            ==
            0,

            calls

        )


        expect(

            result[
                "event"
            ]
            ==
            "UPDATED",

            result

        )


        print(
            "90 SEC HEAVY DELAY → NO RECOVERY: PASS ✅"
        )


        # Rewind heartbeat.

        persisted = (
            paper_store.load_trades()[
                0
            ]
        )


        persisted[
            "last_checked_time_ms"
        ] = original_last


        paper_store.save_trades_atomic(
            [
                persisted
            ]
        )


        # =========================
        # 121 SEC
        # =========================

        result = (
            paper_trader.manage_open_position(

                current_price=
                100.0,

                now_ms=
                original_last
                +
                121_000

            )
        )


        expect(

            calls[
                "count"
            ]
            ==
            1,

            calls

        )


        expect(

            result[
                "event"
            ]
            ==
            "UPDATED",

            result

        )


        print(
            "121 SEC UNOBSERVED → RECOVERY: PASS ✅"
        )


    finally:

        binance_api.get_closed_candles_range = (
            previous_range_fetch
        )


# ==============================
# RECOVERY CONFLICT
# ==============================

def test_recovery_conflict_sl_first():

    reset_state()


    position = (
        open_position(
            "UP"
        )
    )


    original_last = int(
        position[
            "last_checked_time_ms"
        ]
    )


    tp = float(
        position[
            "take_profit_price"
        ]
    )


    sl = float(
        position[
            "stop_loss_price"
        ]
    )


    recovery_df = (
        make_recovery_df([

            {

                "time":
                original_last
                +
                ONE_MINUTE_MS,


                "open":
                100.0,


                "high":
                tp
                +
                2.0,


                "low":
                sl
                -
                2.0,


                "close":
                100.0,


                "volume":
                1.0,


                "close_time":
                original_last
                +
                (
                    2
                    *
                    ONE_MINUTE_MS
                )
                -
                1

            }

        ])
    )


    previous_range_fetch = (
        binance_api.get_closed_candles_range
    )


    try:

        binance_api.get_closed_candles_range = (

            lambda *args, **kwargs:
            recovery_df

        )


        result = (
            paper_trader.manage_open_position(

                current_price=
                100.0,

                now_ms=
                original_last
                +
                121_000

            )
        )


        expect(

            result[
                "event"
            ]
            ==
            "CLOSED",

            result

        )


        expect(

            result[
                "position"
            ][
                "exit_reason"
            ]
            ==
            "STOP_LOSS_CONFLICT",

            result

        )


        expected = (

            sl

            *

            (
                1
                -
                paper_trader.STOP_SLIPPAGE_RATE
            )

        )


        expect(

            abs(
                float(
                    result[
                        "position"
                    ][
                        "exit_price"
                    ]
                )
                -
                expected
            )
            <
            1e-6,

            result

        )


        print(
            "RECOVERY TP+SL CONFLICT → SL FIRST: PASS ✅"
        )


    finally:

        binance_api.get_closed_candles_range = (
            previous_range_fetch
        )


# ==============================
# 72 HOUR TRADER CAP
# ==============================

def test_72_hour_cap():

    calls = {
        "count":
        0
    }


    def fake_range(
            *args,
            **kwargs
    ):

        calls[
            "count"
        ] += 1


        return pd.DataFrame(

            columns=[

                "time",

                "open",

                "high",

                "low",

                "close",

                "volume",

                "close_time"

            ]

        )


    previous_range_fetch = (
        binance_api.get_closed_candles_range
    )


    try:

        binance_api.get_closed_candles_range = (
            fake_range
        )


        # =========================
        # EXACTLY 72 HOURS
        # =========================

        reset_state()


        position = (
            open_position(
                "UP"
            )
        )


        last_checked = int(
            position[
                "last_checked_time_ms"
            ]
        )


        result = (
            paper_trader.manage_open_position(

                current_price=
                100.0,

                now_ms=
                last_checked
                +
                (
                    72
                    *
                    ONE_HOUR_MS
                )

            )
        )


        expect(

            calls[
                "count"
            ]
            ==
            1,

            calls

        )


        expect(

            result[
                "event"
            ]
            ==
            "UPDATED",

            result

        )


        print(
            "72 HOURS RECOVERY PERMITTED: PASS ✅"
        )


        # =========================
        # GREATER THAN 72 HOURS
        # =========================

        reset_state()


        position = (
            open_position(
                "UP"
            )
        )


        last_checked = int(
            position[
                "last_checked_time_ms"
            ]
        )


        calls[
            "count"
        ] = 0


        result = (
            paper_trader.manage_open_position(

                current_price=
                100.0,

                now_ms=
                last_checked
                +
                (
                    72
                    *
                    ONE_HOUR_MS
                )
                +
                1

            )
        )


        expect(

            calls[
                "count"
            ]
            ==
            0,

            (
                "1m recovery API was called "
                "after 72h cap"
            )

        )


        expect(

            result[
                "event"
            ]
            ==
            "STALE_RECOVERY_FAILED",

            result

        )


        print(
            ">72 HOURS → ZERO RECOVERY FETCH: PASS ✅"
        )


        print(
            ">72 HOURS → STALE_RECOVERY_FAILED: PASS ✅"
        )


        blocked = (
            paper_trader.execute_paper_trade(

                eligible_data(
                    direction="DOWN"
                )

            )
        )


        expect(

            blocked[
                "status"
            ]
            ==
            "NO TRADE",

            blocked

        )


        print(
            "STALE POSITION BLOCKS NEW ENTRY: PASS ✅"
        )


    finally:

        # Critical isolation fix.
        binance_api.get_closed_candles_range = (
            previous_range_fetch
        )


# ==============================
# DATA-LAYER 72H CAP
# ==============================

def test_data_layer_72h_cap():

    page_calls = {
        "count":
        0
    }


    def fake_page(
            *args,
            **kwargs
    ):

        page_calls[
            "count"
        ] += 1

        return []


    previous_page_fetch = (
        binance_api._fetch_klines_page
    )


    try:

        binance_api._fetch_klines_page = (
            fake_page
        )


        failed = False


        try:

            binance_api.get_closed_candles_range(

                "BTCUSDT",

                interval="1m",

                start_time=0,

                end_time=
                (
                    72
                    *
                    ONE_HOUR_MS
                )
                +
                1,

                max_hours=72

            )


        except (
            binance_api.RecoveryWindowTooLargeError
        ):

            failed = True


        expect(

            failed,

            "Data-layer 72h cap did not trigger"

        )


        expect(

            page_calls[
                "count"
            ]
            ==
            0,

            (
                "Binance kline request occurred "
                "before 72h rejection"
            )

        )


        print(
            "DATA-LAYER 72H HARD CAP: PASS ✅"
        )


    finally:

        binance_api._fetch_klines_page = (
            previous_page_fetch
        )


# ==============================
# LEGACY POSITION
# ==============================

def test_legacy_position_block():

    reset_state()


    legacy = {

        "time":
        "legacy",


        "symbol":
        "BTCUSDT",


        "action":
        "PAPER BUY",


        "status":
        "OPEN",


        "entry_price":
        78531.97,


        "take_profit":
        0.05,


        "stop_loss":
        0.02

    }


    paper_store.save_trades_atomic(
        [
            legacy
        ]
    )


    result = (
        paper_trader.execute_paper_trade(

            eligible_data(
                direction="UP"
            )

        )
    )


    expect(

        result[
            "status"
        ]
        ==
        "NO TRADE",

        result

    )


    expect(

        "Legacy"
        in
        result[
            "reason"
        ],

        result

    )


    persisted = (
        paper_store.load_trades()[
            0
        ]
    )


    expect(

        "schema_version"
        not in
        persisted,

        (
            "Legacy position was silently "
            "migrated"
        )

    )


    print(
        "LEGACY OPEN DETECTED: PASS ✅"
    )


    print(
        "LEGACY POSITION LEFT UNCHANGED: PASS ✅"
    )


# ==============================
# SHORT PERFORMANCE
# ==============================

def test_short_performance():

    reset_state()


    open_position(
        "DOWN"
    )


    report = (
        performance.generate_performance_report(
            current_price=90.0
        )
    )


    open_report = (
        report[
            "open_position"
        ]
    )


    expect(

        open_report[
            "side"
        ]
        ==
        "SHORT",

        open_report

    )


    expect(

        open_report[
            "gross_unrealized_return"
        ]
        >
        0,

        open_report

    )


    expect(

        open_report[
            "net_unrealized_return"
        ]
        <
        open_report[
            "gross_unrealized_return"
        ],

        open_report

    )


    print(
        "PERFORMANCE SHORT-AWARE: PASS ✅"
    )


# ==============================
# GLOBAL RESTORE
# ==============================

def restore_environment():

    binance_api.get_closed_candles_range = (
        ORIGINAL_RANGE_FETCH
    )


    binance_api._fetch_klines_page = (
        ORIGINAL_PAGE_FETCH
    )


    binance_api.get_server_time = (
        ORIGINAL_SERVER_TIME
    )


    paper_store.TRADE_FILE = (
        ORIGINAL_TRADE_FILE
    )


# ==============================
# RUNNER
# ==============================

def run_tests():

    print(
        "======================================"
    )

    print(
        "ITEM 8 PAPER EXECUTION CONTROLLED TEST"
    )

    print(
        "======================================"
    )


    with tempfile.TemporaryDirectory() as temp_dir:

        paper_store.TRADE_FILE = (
            os.path.join(

                temp_dir,

                "paper_trades_test.json"

            )
        )


        try:

            reset_state()


            test_persistent_state()


            test_corrupt_state_fails_closed()


            test_long_tp_exact()


            test_long_slippage()


            test_long_adverse_gap()


            test_short_tp_and_math()


            test_short_slippage()


            test_recovery_thresholds()


            test_recovery_conflict_sl_first()


            test_72_hour_cap()


            test_data_layer_72h_cap()


            test_legacy_position_block()


            test_short_performance()


        finally:

            restore_environment()


    print(
        "\n======================================"
    )

    print(
        "ITEM 8 CONTROLLED TEST: PASS ✅"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    run_tests()