import datetime
import time
import uuid

import pandas as pd

import data.binance_api as binance_api

from database import paper_store


MIN_PROBABILITY_SAMPLE = 50

STRATEGY_QUALITY_GATE = 70.0

COLLECTION_SIGNAL_GATE = 65.0

CALIBRATED_SIGNAL_GATE = 50.0

PROBABILITY_GATE = 55.0


PAPER_NOTIONAL = 100.0

FEE_RATE = 0.001

STOP_SLIPPAGE_RATE = 0.0005


RECOVERY_THRESHOLD_SECONDS = 120

MAX_OFFLINE_RECOVERY_HOURS = 72


SCHEMA_VERSION = 2


BLOCKING_STATUSES = {
    "OPEN",
    "STALE_RECOVERY_FAILED"
}


def _utc_now_ms():

    return int(
        time.time()
        *
        1000
    )


def _iso_time(
        timestamp_ms
):

    return (
        datetime.datetime
        .fromtimestamp(
            timestamp_ms
            /
            1000,
            tz=datetime.timezone.utc
        )
        .isoformat()
    )


def load_trades():

    return (
        paper_store.load_trades()
    )


def save_all_trades(
        trades
):

    paper_store.save_trades_atomic(
        trades
    )


def save_trade(
        trade
):

    paper_store.append_trade(
        trade
    )


def is_legacy_position(
        position
):

    return (
        int(
            position.get(
                "schema_version",
                0
            )
            or
            0
        )
        <
        SCHEMA_VERSION
    )


def check_open_position():

    trades = (
        load_trades()
    )


    if not trades:

        return None


    for trade in reversed(
        trades
    ):

        if (
            trade.get(
                "status"
            )
            in
            BLOCKING_STATUSES
        ):

            return trade


    return None


def _validate_entry_gates(
        data
):

    strategy_quality = float(
        data.get(
            "strategy_quality",
            0
        )
    )


    signal_strength = float(
        data.get(
            "signal_strength",
            0
        )
    )


    directional_probability = (
        data.get(
            "directional_probability"
        )
    )


    probability_sample = int(
        data.get(
            "directional_probability_sample",
            0
        )
    )


    if (
        strategy_quality
        <
        STRATEGY_QUALITY_GATE
    ):

        return {
            "eligible":
            False,

            "reason":
            "Strategy quality below 70"
        }


    # =========================
    # COLLECTION MODE
    # =========================

    if (
        probability_sample
        <
        MIN_PROBABILITY_SAMPLE
    ):

        if (
            signal_strength
            <
            COLLECTION_SIGNAL_GATE
        ):

            return {
                "eligible":
                False,

                "reason":
                (
                    "Signal strength below 65 "
                    "in collection mode"
                )
            }


        return {
            "eligible":
            True,

            "paper_mode":
            "PAPER_COLLECTION_MODE"
        }


    # =========================
    # CALIBRATED MODE
    # =========================

    if (
        signal_strength
        <
        CALIBRATED_SIGNAL_GATE
    ):

        return {
            "eligible":
            False,

            "reason":
            "Signal strength below 50"
        }


    if (
        directional_probability
        is None
    ):

        return {
            "eligible":
            False,

            "reason":
            "Directional probability unavailable"
        }


    if (
        float(
            directional_probability
        )
        <
        PROBABILITY_GATE
    ):

        return {
            "eligible":
            False,

            "reason":
            "Directional probability below 55%"
        }


    return {
        "eligible":
        True,

        "paper_mode":
        "PAPER_CALIBRATED_MODE"
    }


def execute_paper_trade(
        data
):

    gate = (
        _validate_entry_gates(
            data
        )
    )


    if not gate.get(
        "eligible",
        False
    ):

        return {
            "status":
            "NO TRADE",

            "reason":
            gate.get(
                "reason",
                "Entry gate failed"
            )
        }


    direction = str(
        data.get(
            "direction",
            "FLAT"
        )
    ).upper()


    if direction not in {
        "UP",
        "DOWN"
    }:

        return {
            "status":
            "NO TRADE",

            "reason":
            "No directional trade signal"
        }


    price = float(
        data.get(
            "price",
            0
        )
    )


    if price <= 0:

        return {
            "status":
            "NO TRADE",

            "reason":
            "Invalid price"
        }


    existing = (
        check_open_position()
    )


    if existing:

        if is_legacy_position(
            existing
        ):

            return {
                "status":
                "NO TRADE",

                "reason":
                (
                    "Legacy open position requires "
                    "manual review"
                )
            }


        if (
            existing.get(
                "status"
            )
            ==
            "STALE_RECOVERY_FAILED"
        ):

            return {
                "status":
                "NO TRADE",

                "reason":
                (
                    "Stale recovery position requires "
                    "manual review"
                )
            }


        return {
            "status":
            "NO TRADE",

            "reason":
            "Existing position active"
        }


    strategy_quality = float(
        data.get(
            "strategy_quality",
            0
        )
    )


    signal_strength = float(
        data.get(
            "signal_strength",
            0
        )
    )


    directional_probability = (
        data.get(
            "directional_probability"
        )
    )


    probability_sample = int(
        data.get(
            "directional_probability_sample",
            0
        )
    )


    strategy = data.get(
        "best_strategy",
        {}
    )


    symbol = data.get(
        "symbol",
        "BTCUSDT"
    )


    atr = float(
        data.get(
            "atr",
            0
        )
    )


    # =========================
    # ATR RISK DISTANCES
    # =========================

    if atr > 0:

        stop_loss_rate = round(
            (
                atr
                *
                2
            )
            /
            price,
            4
        )


        take_profit_rate = round(
            (
                atr
                *
                4
            )
            /
            price,
            4
        )


    else:

        stop_loss_rate = 0.02

        take_profit_rate = 0.05


    if direction == "UP":

        side = "LONG"

        action = "PAPER BUY"


        take_profit_price = (
            price
            *
            (
                1
                +
                take_profit_rate
            )
        )


        stop_loss_price = (
            price
            *
            (
                1
                -
                stop_loss_rate
            )
        )


    else:

        side = "SHORT"

        action = "PAPER SHORT"


        take_profit_price = (
            price
            *
            (
                1
                -
                take_profit_rate
            )
        )


        stop_loss_price = (
            price
            *
            (
                1
                +
                stop_loss_rate
            )
        )


    now_ms = (
        _utc_now_ms()
    )


    entry_fee = (
        PAPER_NOTIONAL
        *
        FEE_RATE
    )


    quantity = (
        PAPER_NOTIONAL
        /
        price
    )


    trade = {

        "schema_version":
        SCHEMA_VERSION,


        "position_id":
        uuid.uuid4().hex,


        "symbol":
        symbol,


        "side":
        side,


        "action":
        action,


        "status":
        "OPEN",


        "paper_mode":
        gate[
            "paper_mode"
        ],


        "entry_time_ms":
        now_ms,


        "entry_time":
        _iso_time(
            now_ms
        ),


        "entry_price":
        round(
            price,
            8
        ),


        "notional":
        PAPER_NOTIONAL,


        "quantity":
        round(
            quantity,
            12
        ),


        "fee_rate":
        FEE_RATE,


        "entry_fee":
        round(
            entry_fee,
            8
        ),


        "take_profit_rate":
        take_profit_rate,


        "stop_loss_rate":
        stop_loss_rate,


        # Compatibility aliases.
        "take_profit":
        take_profit_rate,


        "stop_loss":
        stop_loss_rate,


        "take_profit_price":
        round(
            take_profit_price,
            8
        ),


        "stop_loss_price":
        round(
            stop_loss_price,
            8
        ),


        "stop_slippage_rate":
        STOP_SLIPPAGE_RATE,


        "last_checked_time_ms":
        now_ms,


        "last_checked_time":
        _iso_time(
            now_ms
        ),


        "last_checked_price":
        round(
            price,
            8
        ),


        "strategy_quality":
        strategy_quality,


        "signal_strength":
        signal_strength,


        "directional_probability":
        directional_probability,


        "directional_probability_sample":
        probability_sample,


        "atr":
        atr,


        "strategy":
        strategy

    }


    save_trade(
        trade
    )


    print(
        "✅ PAPER POSITION SAVED"
    )


    return trade


def _apply_stop_slippage(
        base_price,
        side
):

    base_price = float(
        base_price
    )


    if side == "LONG":

        return (
            base_price
            *
            (
                1
                -
                STOP_SLIPPAGE_RATE
            )
        )


    return (
        base_price
        *
        (
            1
            +
            STOP_SLIPPAGE_RATE
        )
    )


def _close_position_record(
        position,
        exit_price,
        exit_reason,
        timestamp_ms,
        recovery=False,
        recovery_candle_time=None
):

    closed = dict(
        position
    )


    entry_price = float(
        closed.get(
            "entry_price",
            0
        )
    )


    side = closed.get(
        "side"
    )


    notional = float(
        closed.get(
            "notional",
            PAPER_NOTIONAL
        )
    )


    fee_rate = float(
        closed.get(
            "fee_rate",
            FEE_RATE
        )
    )


    entry_fee = float(
        closed.get(
            "entry_fee",
            notional
            *
            fee_rate
        )
    )


    exit_fee = (
        notional
        *
        fee_rate
    )


    if side == "LONG":

        gross_return_decimal = (
            (
                exit_price
                -
                entry_price
            )
            /
            entry_price
        )


    elif side == "SHORT":

        # Required SHORT formula:
        #
        # (Entry - Exit) / Entry

        gross_return_decimal = (
            (
                entry_price
                -
                exit_price
            )
            /
            entry_price
        )


    else:

        raise ValueError(
            "Unknown paper position side"
        )


    gross_profit = (
        gross_return_decimal
        *
        notional
    )


    fee_cost = (
        entry_fee
        +
        exit_fee
    )


    net_profit = (
        gross_profit
        -
        fee_cost
    )


    net_return_decimal = (
        net_profit
        /
        notional
    )


    closed.update({

        "status":
        "CLOSED",


        "exit_price":
        round(
            float(
                exit_price
            ),
            8
        ),


        "exit_reason":
        exit_reason,


        "exit_time_ms":
        int(
            timestamp_ms
        ),


        "exit_time":
        _iso_time(
            timestamp_ms
        ),


        "closed_time":
        _iso_time(
            timestamp_ms
        ),


        "exit_fee":
        round(
            exit_fee,
            8
        ),


        "fee_cost":
        round(
            fee_cost,
            8
        ),


        "gross_return":
        round(
            gross_return_decimal
            *
            100,
            8
        ),


        "gross_profit":
        round(
            gross_profit,
            8
        ),


        # NET percentage after both fees.
        "return":
        round(
            net_return_decimal
            *
            100,
            8
        ),


        # NET dollar profit after both fees.
        "profit":
        round(
            net_profit,
            8
        ),


        "recovery_exit":
        bool(
            recovery
        )

    })


    if recovery_candle_time is not None:

        closed[
            "recovery_candle_time"
        ] = int(
            recovery_candle_time
        )


    return closed


def _evaluate_ticker_exit(
        position,
        current_price,
        now_ms
):

    side = position.get(
        "side"
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


    current_price = float(
        current_price
    )


    # =========================
    # SL FIRST
    # =========================

    if side == "LONG":

        if current_price <= sl:

            exit_price = (
                _apply_stop_slippage(
                    current_price,
                    side
                )
            )


            return (
                _close_position_record(

                    position,

                    exit_price=

                    exit_price,

                    exit_reason=

                    "STOP_LOSS",

                    timestamp_ms=

                    now_ms

                )
            )


        # TP is limit-style.
        # Exact touch is not guaranteed.

        if current_price > tp:

            return (
                _close_position_record(

                    position,

                    exit_price=

                    tp,

                    exit_reason=

                    "TAKE_PROFIT",

                    timestamp_ms=

                    now_ms

                )
            )


    elif side == "SHORT":

        if current_price >= sl:

            exit_price = (
                _apply_stop_slippage(
                    current_price,
                    side
                )
            )


            return (
                _close_position_record(

                    position,

                    exit_price=

                    exit_price,

                    exit_reason=

                    "STOP_LOSS",

                    timestamp_ms=

                    now_ms

                )
            )


        if current_price < tp:

            return (
                _close_position_record(

                    position,

                    exit_price=

                    tp,

                    exit_reason=

                    "TAKE_PROFIT",

                    timestamp_ms=

                    now_ms

                )
            )


    return None


def _evaluate_recovery_candle(
        position,
        candle
):

    side = position.get(
        "side"
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


    candle_open = float(
        candle[
            "open"
        ]
    )


    candle_high = float(
        candle[
            "high"
        ]
    )


    candle_low = float(
        candle[
            "low"
        ]
    )


    candle_time = int(
        candle[
            "time"
        ]
    )


    close_time = int(
        candle.get(
            "close_time",
            candle_time
        )
    )


    # =========================
    # LONG
    # =========================

    if side == "LONG":

        # Adverse gap through SL.
        if candle_open <= sl:

            exit_price = (
                _apply_stop_slippage(
                    candle_open,
                    side
                )
            )


            return (
                _close_position_record(

                    position,

                    exit_price=

                    exit_price,

                    exit_reason=

                    "STOP_LOSS_GAP",

                    timestamp_ms=

                    candle_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


        # Favorable TP gap.
        if candle_open > tp:

            return (
                _close_position_record(

                    position,

                    exit_price=

                    tp,

                    exit_reason=

                    "TAKE_PROFIT",

                    timestamp_ms=

                    candle_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


        sl_hit = (
            candle_low
            <=
            sl
        )


        tp_hit = (
            candle_high
            >
            tp
        )


        # Conservative conflict rule.
        if sl_hit:

            exit_price = (
                _apply_stop_slippage(
                    sl,
                    side
                )
            )


            return (
                _close_position_record(

                    position,

                    exit_price=

                    exit_price,

                    exit_reason=

                    (
                        "STOP_LOSS_CONFLICT"
                        if tp_hit
                        else
                        "STOP_LOSS"
                    ),

                    timestamp_ms=

                    close_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


        if tp_hit:

            return (
                _close_position_record(

                    position,

                    exit_price=

                    tp,

                    exit_reason=

                    "TAKE_PROFIT",

                    timestamp_ms=

                    close_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


    # =========================
    # SHORT
    # =========================

    elif side == "SHORT":

        if candle_open >= sl:

            exit_price = (
                _apply_stop_slippage(
                    candle_open,
                    side
                )
            )


            return (
                _close_position_record(

                    position,

                    exit_price=

                    exit_price,

                    exit_reason=

                    "STOP_LOSS_GAP",

                    timestamp_ms=

                    candle_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


        if candle_open < tp:

            return (
                _close_position_record(

                    position,

                    exit_price=

                    tp,

                    exit_reason=

                    "TAKE_PROFIT",

                    timestamp_ms=

                    candle_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


        sl_hit = (
            candle_high
            >=
            sl
        )


        tp_hit = (
            candle_low
            <
            tp
        )


        if sl_hit:

            exit_price = (
                _apply_stop_slippage(
                    sl,
                    side
                )
            )


            return (
                _close_position_record(

                    position,

                    exit_price=

                    exit_price,

                    exit_reason=

                    (
                        "STOP_LOSS_CONFLICT"
                        if tp_hit
                        else
                        "STOP_LOSS"
                    ),

                    timestamp_ms=

                    close_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


        if tp_hit:

            return (
                _close_position_record(

                    position,

                    exit_price=

                    tp,

                    exit_reason=

                    "TAKE_PROFIT",

                    timestamp_ms=

                    close_time,

                    recovery=True,

                    recovery_candle_time=
                    candle_time

                )
            )


    return None


def _process_recovery_candles(
        position,
        candles
):

    if (
        candles is None
        or
        len(
            candles
        )
        ==
        0
    ):

        return None


    candles = (
        candles
        .sort_values(
            "time"
        )
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
        .reset_index(
            drop=True
        )
    )


    for _, candle in candles.iterrows():

        closed = (
            _evaluate_recovery_candle(
                position,
                candle
            )
        )


        if closed:

            return closed


    return None


def _mark_stale_recovery_failed(
        position,
        now_ms,
        offline_ms
):

    stale = dict(
        position
    )


    stale.update({

        "status":
        "STALE_RECOVERY_FAILED",


        "stale_recovery_failed_time_ms":
        now_ms,


        "stale_recovery_failed_time":
        _iso_time(
            now_ms
        ),


        "offline_duration_seconds":
        round(
            offline_ms
            /
            1000,
            2
        ),


        "recovery_failure_reason":
        (
            "Offline window exceeded "
            f"{MAX_OFFLINE_RECOVERY_HOURS} hours. "
            "Automatic 1m recovery was not attempted."
        )

    })


    paper_store.replace_trade(
        stale
    )


    return stale


def manage_open_position(
        current_price,
        symbol=None,
        now_ms=None
):

    position = (
        check_open_position()
    )


    if not position:

        return {
            "event":
            "NONE",

            "position":
            None
        }


    if is_legacy_position(
        position
    ):

        return {
            "event":
            "LEGACY_OPEN_POSITION",

            "position":
            position
        }


    if (
        position.get(
            "status"
        )
        ==
        "STALE_RECOVERY_FAILED"
    ):

        return {
            "event":
            "STALE_RECOVERY_FAILED",

            "position":
            position
        }


    if (
        position.get(
            "status"
        )
        !=
        "OPEN"
    ):

        return {
            "event":
            "NONE",

            "position":
            position
        }


    if now_ms is None:

        now_ms = (
            _utc_now_ms()
        )


    now_ms = int(
        now_ms
    )


    if symbol is None:

        symbol = position.get(
            "symbol",
            "BTCUSDT"
        )


    last_checked_ms = int(
        position.get(
            "last_checked_time_ms",
            position.get(
                "entry_time_ms",
                now_ms
            )
        )
    )


    offline_ms = max(
        0,
        now_ms
        -
        last_checked_ms
    )


    max_offline_ms = (
        MAX_OFFLINE_RECOVERY_HOURS
        *
        60
        *
        60
        *
        1000
    )


    # =========================
    # HARD 72-HOUR CAP
    # =========================

    if offline_ms > max_offline_ms:

        stale = (
            _mark_stale_recovery_failed(

                position,

                now_ms=

                now_ms,

                offline_ms=

                offline_ms

            )
        )


        return {
            "event":
            "STALE_RECOVERY_FAILED",

            "position":
            stale
        }


    # =========================
    # MISSED-WINDOW RECOVERY
    # =========================

    if (
        offline_ms
        >
        RECOVERY_THRESHOLD_SECONDS
        *
        1000
    ):

        try:

            candles = (
                binance_api.get_closed_candles_range(

                    symbol=

                    symbol,

                    interval=

                    "1m",

                    start_time=

                    last_checked_ms,

                    end_time=

                    now_ms,

                    max_hours=

                    MAX_OFFLINE_RECOVERY_HOURS

                )
            )


        except binance_api.RecoveryWindowTooLargeError:

            stale = (
                _mark_stale_recovery_failed(

                    position,

                    now_ms=

                    now_ms,

                    offline_ms=

                    offline_ms

                )
            )


            return {
                "event":
                "STALE_RECOVERY_FAILED",

                "position":
                stale
            }


        except Exception as error:

            # Fail closed.
            #
            # last_checked_time is NOT advanced.
            # Existing position continues blocking
            # any new entry.

            return {
                "event":
                "RECOVERY_ERROR",

                "position":
                position,

                "error":
                str(
                    error
                )
            }


        recovered_close = (
            _process_recovery_candles(
                position,
                candles
            )
        )


        if recovered_close:

            paper_store.replace_trade(
                recovered_close
            )


            return {
                "event":
                "CLOSED",

                "position":
                recovered_close
            }


    # =========================
    # CURRENT TICKER
    # =========================

    ticker_close = (
        _evaluate_ticker_exit(

            position,

            current_price=

            current_price,

            now_ms=

            now_ms

        )
    )


    if ticker_close:

        paper_store.replace_trade(
            ticker_close
        )


        return {
            "event":
            "CLOSED",

            "position":
            ticker_close
        }


    # =========================
    # PERSIST HEARTBEAT
    # =========================

    updated = dict(
        position
    )


    updated.update({

        "last_checked_time_ms":
        now_ms,


        "last_checked_time":
        _iso_time(
            now_ms
        ),


        "last_checked_price":
        round(
            float(
                current_price
            ),
            8
        )

    })


    paper_store.replace_trade(
        updated
    )


    return {
        "event":
        "UPDATED",

        "position":
        updated
    }


def close_position(
        price
):

    """
    Backward-compatible wrapper.

    Returns the closed trade only when an
    actual close occurred.
    """

    result = (
        manage_open_position(
            price
        )
    )


    if (
        result.get(
            "event"
        )
        ==
        "CLOSED"
    ):

        return result.get(
            "position"
        )


    return None