import json
import os


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

MIN_DIRECTIONAL_SAMPLES = 50


def load_decisions():

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
            "⚠️ V3 Probability Read Error:",
            e
        )

        return []


def is_active_prediction(
    decision
):

    if not isinstance(
        decision,
        dict
    ):

        return False

    if decision.get(
        "version"
    ) != ACTIVE_VERSION:

        return False

    if decision.get(
        "timing_model"
    ) != TIMING_MODEL:

        return False

    if decision.get(
        "label_model"
    ) != LABEL_MODEL:

        return False

    return True


def get_directional_probability(
    direction,
    decisions=None,
    minimum_samples=
    MIN_DIRECTIONAL_SAMPLES
):

    """
    Estimate direction-specific probability
    using clean threshold V3 labels.

    NEUTRAL receives 0.5 outcome credit:

        numerator =
        CORRECT
        + 0.5 * NEUTRAL
        + 1

        denominator =
        CORRECT
        + WRONG
        + NEUTRAL
        + 2

    The +1 / +2 terms provide Beta-style
    smoothing toward 50%.

    Probability is not exposed as calibrated
    until minimum_samples are available.
    """

    direction = str(
        direction
    ).upper()

    if direction not in [
        "UP",
        "DOWN"
    ]:

        return {
            "direction":
            direction,

            "status":
            "NO_DIRECTION",

            "directional_probability":
            None,

            "smoothed_estimate":
            None,

            "sample":
            0,

            "correct":
            0,

            "wrong":
            0,

            "neutral":
            0,

            "conditional_accuracy":
            None
        }

    if decisions is None:

        decisions = (
            load_decisions()
        )

    evaluated = [

        item

        for item in decisions

        if (
            is_active_prediction(
                item
            )

            and

            item.get(
                "direction"
            ) == direction

            and

            item.get(
                "result"
            ) in [
                "CORRECT",
                "WRONG",
                "NEUTRAL"
            ]
        )
    ]

    correct = len([
        item
        for item in evaluated
        if item.get(
            "result"
        ) == "CORRECT"
    ])

    wrong = len([
        item
        for item in evaluated
        if item.get(
            "result"
        ) == "WRONG"
    ])

    neutral = len([
        item
        for item in evaluated
        if item.get(
            "result"
        ) == "NEUTRAL"
    ])

    sample = (
        correct
        +
        wrong
        +
        neutral
    )

    directional_outcomes = (
        correct
        +
        wrong
    )

    numerator = (
        correct
        +
        (
            0.5
            *
            neutral
        )
        +
        1
    )

    denominator = (
        sample
        +
        2
    )

    smoothed_estimate = round(
        (
            numerator
            /
            denominator
        )
        *
        100,
        2
    )

    if directional_outcomes > 0:

        conditional_accuracy = round(
            (
                correct
                /
                directional_outcomes
            )
            *
            100,
            2
        )

    else:

        conditional_accuracy = None

    if directional_outcomes >= int(
        minimum_samples
    ):

        probability = (
            smoothed_estimate
        )

        status = (
            "CALIBRATED"
        )

    else:

        probability = None

        status = (
            "INSUFFICIENT_DATA"
        )

    return {
        "direction":
        direction,

        "status":
        status,

        "directional_probability":
        probability,

        "smoothed_estimate":
        smoothed_estimate,

        "sample":
        sample,

        "directional_outcomes":
        directional_outcomes,

        "minimum_sample":
        int(
            minimum_samples
        ),

        "correct":
        correct,

        "wrong":
        wrong,

        "neutral":
        neutral,

        "conditional_accuracy":
        conditional_accuracy
    }


def print_directional_probability(
    direction
):

    stats = (
        get_directional_probability(
            direction
        )
    )

    print(
        "\n📊 DIRECTIONAL PROBABILITY"
    )

    print(
        "Direction:",
        stats[
            "direction"
        ]
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
        "Status:",
        stats[
            "status"
        ]
    )

    return stats