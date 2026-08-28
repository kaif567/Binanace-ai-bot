import json
import os
import datetime
import math


LOG_FILE = (
    "ai_decisions_v3.json"
)

ACTIVE_VERSION = 3

ONE_HOUR_MS = (
    60
    *
    60
    *
    1000
)

TIMING_MODEL = (
    "CLOSED_CANDLE_NEXT_CLOSED_CANDLE"
)

LABEL_MODEL = (
    "FEES_PLUS_ATR_THRESHOLD_V1"
)

METRIC_MODEL = (
    "SEPARATED_METRICS_V1"
)


FEE_PER_SIDE_PERCENT = 0.10

ROUND_TRIP_FEE_PERCENT = (
    FEE_PER_SIDE_PERCENT
    *
    2
)

ATR_FRACTION = 0.25


def utc_now():

    return (
        datetime.datetime.now(
            datetime.timezone.utc
        )
        .isoformat()
    )


def format_utc_timestamp(
    timestamp_ms
):

    if timestamp_ms is None:
        return None

    try:

        timestamp_ms = int(
            timestamp_ms
        )

        dt = (
            datetime.datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=datetime.timezone.utc
            )
        )

        return dt.strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    except Exception:

        return str(
            timestamp_ms
        )


def is_valid_number(
    value
):

    try:

        return math.isfinite(
            float(value)
        )

    except Exception:

        return False


def load_logs():

    if not os.path.exists(
        LOG_FILE
    ):

        return []

    try:

        with open(
            LOG_FILE,
            "r"
        ) as f:

            data = json.load(
                f
            )

        if not isinstance(
            data,
            list
        ):

            return []

        return data

    except Exception as e:

        print(
            "⚠️ V3 Log Read Error:",
            e
        )

        return []


def save_all_logs(
    logs
):

    with open(
        LOG_FILE,
        "w"
    ) as f:

        json.dump(
            logs,
            f,
            indent=4
        )


def is_v3_timing_record(
    item
):

    if not isinstance(
        item,
        dict
    ):

        return False

    if item.get(
        "version"
    ) != ACTIVE_VERSION:

        return False

    if item.get(
        "timing_model"
    ) != TIMING_MODEL:

        return False

    return True


def is_active_threshold_record(
    item
):

    if not is_v3_timing_record(
        item
    ):

        return False

    return (
        item.get(
            "label_model"
        )
        ==
        LABEL_MODEL
    )


def prediction_exists_for_candle(
    signal_candle_open_time,
    logs=None
):

    if logs is None:

        logs = load_logs()

    signal_candle_open_time = int(
        signal_candle_open_time
    )

    for item in reversed(
        logs
    ):

        if not is_v3_timing_record(
            item
        ):

            continue

        existing_time = (
            item.get(
                "signal_candle_open_time"
            )
        )

        if existing_time is None:

            continue

        if int(
            existing_time
        ) == signal_candle_open_time:

            return True

    return False


def calculate_threshold(
    signal_price,
    signal_atr
):

    signal_price = float(
        signal_price
    )

    signal_atr = float(
        signal_atr
    )

    if signal_price <= 0:

        raise ValueError(
            "Signal price must be greater than 0"
        )

    if (
        not is_valid_number(
            signal_atr
        )

        or

        signal_atr <= 0
    ):

        raise ValueError(
            "Signal ATR must be positive"
        )

    signal_atr_percent = (

        signal_atr
        /
        signal_price

    ) * 100

    atr_threshold_percent = (

        signal_atr_percent
        *
        ATR_FRACTION
    )

    minimum_move_threshold_percent = (

        ROUND_TRIP_FEE_PERCENT
        +
        atr_threshold_percent
    )

    return {
        "signal_atr":
        round(
            signal_atr,
            8
        ),

        "signal_atr_percent":
        round(
            signal_atr_percent,
            6
        ),

        "fee_per_side_percent":
        FEE_PER_SIDE_PERCENT,

        "round_trip_fee_percent":
        ROUND_TRIP_FEE_PERCENT,

        "atr_fraction":
        ATR_FRACTION,

        "atr_threshold_percent":
        round(
            atr_threshold_percent,
            6
        ),

        "minimum_move_threshold_percent":
        round(
            minimum_move_threshold_percent,
            6
        )
    }


def save_ai_decision(
    price,
    strategy_quality,
    signal_strength,
    directional_probability,
    directional_probability_sample,
    strategy,
    signal,
    direction,
    market_score,
    signal_candle_open_time,
    signal_atr
):

    logs = load_logs()

    signal_candle_open_time = int(
        signal_candle_open_time
    )

    if prediction_exists_for_candle(
        signal_candle_open_time,
        logs=logs
    ):

        return None

    threshold_data = (
        calculate_threshold(
            price,
            signal_atr
        )
    )

    signal_candle_close_time = (
        signal_candle_open_time
        +
        ONE_HOUR_MS
    )

    target_candle_open_time = (
        signal_candle_close_time
    )

    target_candle_close_time = (
        target_candle_open_time
        +
        ONE_HOUR_MS
    )

    if direction in [
        "UP",
        "DOWN"
    ]:

        result = "PENDING"

    else:

        result = "SKIPPED"

    created_time = utc_now()

    decision = {
        "id":
        len(logs) + 1,

        "version":
        ACTIVE_VERSION,

        "dataset":
        "V3_CLEAN",

        "timing_model":
        TIMING_MODEL,

        "label_model":
        LABEL_MODEL,

        "metric_model":
        METRIC_MODEL,

        "time":
        created_time,

        "prediction_created_time":
        created_time,

        "signal_candle_open_time":
        signal_candle_open_time,

        "signal_candle_close_time":
        signal_candle_close_time,

        "target_candle_open_time":
        target_candle_open_time,

        "target_candle_close_time":
        target_candle_close_time,

        "prediction_horizon_minutes":
        60,

        "reference_price_type":
        "SIGNAL_CANDLE_CLOSE",

        "evaluation_price_type":
        "TARGET_CANDLE_CLOSE",

        "price":
        float(
            price
        ),

        "strategy_quality":
        float(
            strategy_quality
        ),

        "signal_strength":
        float(
            signal_strength
        ),

        "directional_probability":
        (
            None
            if directional_probability
            is None
            else
            float(
                directional_probability
            )
        ),

        "directional_probability_sample":
        int(
            directional_probability_sample
        ),

        "market_score":
        float(
            market_score
        ),

        "signal":
        signal,

        "direction":
        direction,

        "strategy":
        strategy,

        "signal_atr":
        threshold_data[
            "signal_atr"
        ],

        "signal_atr_percent":
        threshold_data[
            "signal_atr_percent"
        ],

        "fee_per_side_percent":
        threshold_data[
            "fee_per_side_percent"
        ],

        "round_trip_fee_percent":
        threshold_data[
            "round_trip_fee_percent"
        ],

        "atr_fraction":
        threshold_data[
            "atr_fraction"
        ],

        "atr_threshold_percent":
        threshold_data[
            "atr_threshold_percent"
        ],

        "minimum_move_threshold_percent":
        threshold_data[
            "minimum_move_threshold_percent"
        ],

        "future_price":
        None,

        "future_candle_time":
        None,

        "price_change_percent":
        None,

        "actual_horizon_minutes":
        None,

        "evaluated_time":
        None,

        "result":
        result
    }

    logs.append(
        decision
    )

    save_all_logs(
        logs
    )

    print(
        "\n🧠 V3 SEPARATED-METRIC PREDICTION SAVED"
    )

    print(
        "V3 ID:",
        decision["id"]
    )

    print(
        "Strategy Quality:",
        decision[
            "strategy_quality"
        ]
    )

    print(
        "Signal Strength:",
        decision[
            "signal_strength"
        ]
    )

    print(
        "Directional Probability:",
        decision[
            "directional_probability"
        ]
    )

    print(
        "Probability Sample:",
        decision[
            "directional_probability_sample"
        ]
    )

    print(
        "Minimum Move Threshold %:",
        decision[
            "minimum_move_threshold_percent"
        ]
    )

    return decision


def evaluate_pending_predictions(
    closed_df
):

    logs = load_logs()

    if not logs:

        return []

    if (
        closed_df is None
        or
        len(closed_df) == 0
    ):

        return []

    if (
        "time"
        not in closed_df.columns

        or

        "close"
        not in closed_df.columns
    ):

        raise ValueError(
            "closed_df must contain time and close"
        )

    closed_candle_prices = {}

    for _, row in closed_df.iterrows():

        candle_open_time = int(
            row["time"]
        )

        closed_candle_prices[
            candle_open_time
        ] = float(
            row["close"]
        )

    updated = []

    for decision in logs:

        # Important:
        # older threshold-era V3 records
        # remain valid for evaluation.
        if not is_active_threshold_record(
            decision
        ):

            continue

        if decision.get(
            "result"
        ) != "PENDING":

            continue

        target_time = (
            decision.get(
                "target_candle_open_time"
            )
        )

        if target_time is None:

            continue

        target_time = int(
            target_time
        )

        if target_time not in (
            closed_candle_prices
        ):

            continue

        entry_price = float(
            decision.get(
                "price",
                0
            )
        )

        if entry_price <= 0:

            continue

        future_price = float(
            closed_candle_prices[
                target_time
            ]
        )

        change_percent = (

            (
                future_price
                -
                entry_price
            )

            /

            entry_price

        ) * 100

        threshold = float(
            decision.get(
                "minimum_move_threshold_percent",
                0
            )
        )

        if threshold <= 0:

            continue

        direction = decision.get(
            "direction",
            "FLAT"
        )

        if direction == "UP":

            if (
                change_percent
                >=
                threshold
            ):

                result = "CORRECT"

            elif (
                change_percent
                <=
                -threshold
            ):

                result = "WRONG"

            else:

                result = "NEUTRAL"

        elif direction == "DOWN":

            if (
                change_percent
                <=
                -threshold
            ):

                result = "CORRECT"

            elif (
                change_percent
                >=
                threshold
            ):

                result = "WRONG"

            else:

                result = "NEUTRAL"

        else:

            result = "SKIPPED"

        decision[
            "future_price"
        ] = future_price

        decision[
            "future_candle_time"
        ] = target_time

        decision[
            "price_change_percent"
        ] = round(
            change_percent,
            6
        )

        decision[
            "actual_horizon_minutes"
        ] = 60

        decision[
            "evaluated_time"
        ] = utc_now()

        decision[
            "result"
        ] = result

        updated.append(
            decision
        )

    if updated:

        save_all_logs(
            logs
        )

        print(
            "\n✅ V3 PREDICTIONS EVALUATED:",
            len(updated)
        )

        for decision in updated:

            print(
                "V3 ID:",
                decision.get(
                    "id"
                )
            )

            print(
                "Move %:",
                decision.get(
                    "price_change_percent"
                )
            )

            print(
                "Required Threshold %:",
                decision.get(
                    "minimum_move_threshold_percent"
                )
            )

            print(
                "Result:",
                decision.get(
                    "result"
                )
            )

    return updated


def get_recent_decisions(
    limit=5
):

    logs = load_logs()

    active = [
        item
        for item in logs
        if is_active_threshold_record(
            item
        )
    ]

    return active[
        -limit:
    ]


def print_ai_history():

    decisions = (
        get_recent_decisions()
    )

    print(
        "\n=============================="
    )

    print(
        "🧠 AI V3 HISTORY"
    )

    print(
        "=============================="
    )

    if not decisions:

        print(
            "No threshold-era V3 predictions yet"
        )

        return

    for item in decisions:

        print(
            "\nV3 ID:",
            item.get(
                "id"
            )
        )

        print(
            "Direction:",
            item.get(
                "direction"
            )
        )

        print(
            "Signal:",
            item.get(
                "signal"
            )
        )

        print(
            "Market Score:",
            item.get(
                "market_score"
            )
        )

        if (
            item.get(
                "metric_model"
            )
            ==
            METRIC_MODEL
        ):

            print(
                "Strategy Quality:",
                item.get(
                    "strategy_quality"
                )
            )

            print(
                "Signal Strength:",
                item.get(
                    "signal_strength"
                )
            )

            print(
                "Directional Probability:",
                item.get(
                    "directional_probability"
                )
            )

            print(
                "Probability Sample:",
                item.get(
                    "directional_probability_sample"
                )
            )

        else:

            print(
                "Metric Model:",
                "PRE-SEPARATION V3"
            )

        print(
            "Threshold %:",
            item.get(
                "minimum_move_threshold_percent"
            )
        )

        print(
            "Target Evaluation:",
            format_utc_timestamp(
                item.get(
                    "target_candle_close_time"
                )
            )
        )

        print(
            "Future Price:",
            item.get(
                "future_price"
            )
        )

        print(
            "Move %:",
            item.get(
                "price_change_percent"
            )
        )

        print(
            "Result:",
            item.get(
                "result"
            )
        )