import json
import os

from database.confidence import (
    get_directional_probability
)


LOG_FILE = (
    "ai_decisions_v3.json"
)

ACTIVE_VERSION = 3

TIMING_MODEL = (
    "CLOSED_CANDLE_NEXT_CLOSED_CANDLE"
)

LABEL_MODEL = (
    "FEES_PLUS_ATR_THRESHOLD_V1"
)

METRIC_MODEL = (
    "SEPARATED_METRICS_V1"
)


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
            "V3 Log Read Error:",
            e
        )

        return []


def is_active_threshold_record(
    item
):

    return (
        isinstance(
            item,
            dict
        )

        and

        item.get(
            "version"
        ) == ACTIVE_VERSION

        and

        item.get(
            "timing_model"
        ) == TIMING_MODEL

        and

        item.get(
            "label_model"
        ) == LABEL_MODEL
    )


def average(
    values
):

    if not values:

        return None

    return round(
        sum(
            values
        )
        /
        len(
            values
        ),
        2
    )


def analyze():

    logs = load_logs()

    active = [
        item
        for item in logs
        if is_active_threshold_record(
            item
        )
    ]

    separated = [
        item
        for item in active
        if item.get(
            "metric_model"
        ) == METRIC_MODEL
    ]

    completed = [
        item
        for item in active
        if item.get(
            "result"
        ) in [
            "CORRECT",
            "WRONG"
        ]
    ]

    correct = len([
        item
        for item in completed
        if item.get(
            "result"
        ) == "CORRECT"
    ])

    wrong = len([
        item
        for item in completed
        if item.get(
            "result"
        ) == "WRONG"
    ])

    neutral = len([
        item
        for item in active
        if item.get(
            "result"
        ) == "NEUTRAL"
    ])

    pending = len([
        item
        for item in active
        if item.get(
            "result"
        ) == "PENDING"
    ])

    skipped = len([
        item
        for item in active
        if item.get(
            "result"
        ) == "SKIPPED"
    ])

    print(
        "=============================="
    )

    print(
        "📊 V3 SEPARATED METRIC ANALYSIS"
    )

    print(
        "=============================="
    )

    print(
        "Threshold Records:",
        len(
            active
        )
    )

    print(
        "Separated Metric Records:",
        len(
            separated
        )
    )

    print(
        "Correct:",
        correct
    )

    print(
        "Wrong:",
        wrong
    )

    print(
        "Neutral:",
        neutral
    )

    print(
        "Pending:",
        pending
    )

    print(
        "Skipped:",
        skipped
    )

    # =========================
    # STRATEGY QUALITY
    # =========================

    qualities = []

    strengths = []

    for item in separated:

        try:

            qualities.append(
                float(
                    item[
                        "strategy_quality"
                    ]
                )
            )

        except Exception:
            pass

        try:

            strengths.append(
                float(
                    item[
                        "signal_strength"
                    ]
                )
            )

        except Exception:
            pass

    print(
        "\n=============================="
    )

    print(
        "🏆 STRATEGY QUALITY ANALYSIS"
    )

    print(
        "=============================="
    )

    print(
        "Average Strategy Quality:",
        average(
            qualities
        )
    )

    print(
        "Samples:",
        len(
            qualities
        )
    )

    print(
        "\n=============================="
    )

    print(
        "⚡ SIGNAL STRENGTH ANALYSIS"
    )

    print(
        "=============================="
    )

    print(
        "Average Signal Strength:",
        average(
            strengths
        )
    )

    print(
        "Samples:",
        len(
            strengths
        )
    )

    # =========================
    # DIRECTIONAL PROBABILITY
    # =========================

    print(
        "\n=============================="
    )

    print(
        "🎯 DIRECTIONAL PROBABILITY ANALYSIS"
    )

    print(
        "=============================="
    )

    for direction in [
        "UP",
        "DOWN"
    ]:

        stats = (
            get_directional_probability(
                direction,
                decisions=active
            )
        )

        print(
            "\nDirection:",
            direction
        )

        print(
            "Sample:",
            stats[
                "sample"
            ]
        )

        print(
            "Correct:",
            stats[
                "correct"
            ]
        )

        print(
            "Wrong:",
            stats[
                "wrong"
            ]
        )

        print(
            "Neutral:",
            stats[
                "neutral"
            ]
        )

        print(
            "Conditional Accuracy:",
            stats[
                "conditional_accuracy"
            ]
        )

        print(
            "Smoothed Estimate:",
            stats[
                "smoothed_estimate"
            ]
        )

        print(
            "Calibrated Probability:",
            stats[
                "directional_probability"
            ]
        )

        print(
            "Probability Status:",
            stats[
                "status"
            ]
        )


if __name__ == "__main__":

    analyze()