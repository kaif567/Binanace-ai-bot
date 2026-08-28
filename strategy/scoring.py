import math


def _is_valid(value):

    try:
        return math.isfinite(
            float(value)
        )

    except Exception:
        return False


def _get_strategy_params(strategy):

    if not isinstance(
        strategy,
        dict
    ):
        return {}

    nested = strategy.get(
        "strategy"
    )

    if isinstance(
        nested,
        dict
    ):
        return nested

    return strategy


def _get_ema_columns(
    current,
    strategy=None
):

    params = _get_strategy_params(
        strategy
    )

    ema_fast = params.get(
        "ema_fast",
        20
    )

    ema_slow = params.get(
        "ema_slow",
        50
    )

    ema_text = params.get(
        "ema"
    )

    if isinstance(
        ema_text,
        str
    ):

        try:

            fast_text, slow_text = (
                ema_text.split("/")
            )

            ema_fast = int(
                fast_text
            )

            ema_slow = int(
                slow_text
            )

        except Exception:
            pass

    fast_column = (
        f"ema{ema_fast}"
    )

    slow_column = (
        f"ema{ema_slow}"
    )

    if (
        fast_column
        not in current.index

        or

        slow_column
        not in current.index
    ):

        fast_column = "ema20"
        slow_column = "ema50"

    return (
        fast_column,
        slow_column
    )


def _neutral_result(
    reason
):

    return {
        "score":
        50.0,

        "market_score":
        50.0,

        "signal":
        "HOLD",

        "direction":
        "FLAT",

        "signal_strength":
        0.0,

        # compatibility alias
        "strength":
        0.0,

        "reasons": [
            reason
        ]
    }


def calculate_market_score(
    current,
    previous,
    strategy=None
):

    score = 50.0

    reasons = []

    fast_column, slow_column = (
        _get_ema_columns(
            current,
            strategy
        )
    )

    required = [
        current.get(
            fast_column
        ),

        current.get(
            slow_column
        ),

        current.get(
            "rsi"
        ),

        current.get(
            "macd"
        ),

        current.get(
            "macd_signal"
        ),

        current.get(
            "close"
        ),

        previous.get(
            "close"
        )
    ]

    if not all(
        _is_valid(value)
        for value in required
    ):

        return _neutral_result(
            "Indicators not ready"
        )

    price = float(
        current["close"]
    )

    previous_price = float(
        previous["close"]
    )

    # =========================
    # EMA TREND
    # =========================

    ema_fast = float(
        current[
            fast_column
        ]
    )

    ema_slow = float(
        current[
            slow_column
        ]
    )

    if ema_fast > ema_slow:

        score += 20

        reasons.append(
            "EMA trend bullish"
        )

    else:

        score -= 20

        reasons.append(
            "EMA trend bearish"
        )

    # =========================
    # RSI
    # =========================

    rsi = float(
        current["rsi"]
    )

    previous_rsi = (
        previous.get(
            "rsi"
        )
    )

    if rsi < 30:

        if (
            _is_valid(
                previous_rsi
            )

            and

            rsi
            >
            float(
                previous_rsi
            )
        ):

            score += 10

            reasons.append(
                "RSI oversold recovery"
            )

        else:

            score -= 5

            reasons.append(
                "RSI oversold but weak"
            )

    elif 30 <= rsi < 45:

        score -= 5

        reasons.append(
            "RSI bearish zone"
        )

    elif 45 <= rsi <= 65:

        score += 10

        reasons.append(
            "RSI supports bullish momentum"
        )

    elif rsi > 70:

        score -= 10

        reasons.append(
            "RSI overbought"
        )

    # =========================
    # MACD
    # =========================

    macd = float(
        current["macd"]
    )

    macd_signal = float(
        current[
            "macd_signal"
        ]
    )

    macd_gap = (
        macd
        -
        macd_signal
    )

    previous_macd = (
        previous.get(
            "macd"
        )
    )

    previous_macd_signal = (
        previous.get(
            "macd_signal"
        )
    )

    if macd_gap > 0:

        score += 15

        reasons.append(
            "MACD bullish"
        )

    else:

        score -= 15

        reasons.append(
            "MACD bearish"
        )

    if (
        _is_valid(
            previous_macd
        )

        and

        _is_valid(
            previous_macd_signal
        )
    ):

        previous_gap = (

            float(
                previous_macd
            )

            -

            float(
                previous_macd_signal
            )
        )

        if (
            macd_gap
            >
            previous_gap
        ):

            score += 5

            reasons.append(
                "MACD momentum improving"
            )

        elif (
            macd_gap
            <
            previous_gap
        ):

            score -= 5

            reasons.append(
                "MACD momentum weakening"
            )

    # =========================
    # PRICE MOMENTUM
    # =========================

    price_change = (

        price
        -
        previous_price

    ) / previous_price

    if price_change > 0:

        score += 10

        reasons.append(
            "Positive price momentum"
        )

    elif price_change < 0:

        score -= 10

        reasons.append(
            "Negative price momentum"
        )

    # =========================
    # VOLUME
    # =========================

    volume = current.get(
        "volume"
    )

    volume_avg = current.get(
        "volume_avg"
    )

    if (
        _is_valid(
            volume
        )

        and

        _is_valid(
            volume_avg
        )

        and

        float(
            volume_avg
        ) > 0
    ):

        volume_ratio = (

            float(
                volume
            )

            /

            float(
                volume_avg
            )
        )

        if volume_ratio >= 1.20:

            if price_change > 0:

                score += 10

                reasons.append(
                    "High volume confirms bullish move"
                )

            elif price_change < 0:

                score -= 10

                reasons.append(
                    "High volume confirms bearish move"
                )

    # =========================
    # ADX
    # =========================

    adx = current.get(
        "adx"
    )

    if _is_valid(
        adx
    ):

        adx = float(
            adx
        )

        if adx >= 25:

            if score > 50:

                score += 5

            elif score < 50:

                score -= 5

            reasons.append(
                "ADX confirms strong trend"
            )

        elif adx < 20:

            score = (

                50

                +

                (
                    score
                    -
                    50
                )
                *
                0.80
            )

            reasons.append(
                "ADX shows weak trend"
            )

    # =========================
    # BOLLINGER
    # =========================

    bb_high = current.get(
        "bb_high"
    )

    bb_low = current.get(
        "bb_low"
    )

    if (
        _is_valid(
            bb_high
        )

        and

        _is_valid(
            bb_low
        )
    ):

        if (
            price
            <=
            float(
                bb_low
            )

            and

            rsi < 40
        ):

            score += 5

            reasons.append(
                "Price near lower Bollinger Band"
            )

        elif (
            price
            >=
            float(
                bb_high
            )

            and

            rsi > 60
        ):

            score -= 5

            reasons.append(
                "Price near upper Bollinger Band"
            )

    # =========================
    # FINAL
    # =========================

    score = max(
        0,
        min(
            score,
            100
        )
    )

    score = round(
        score,
        2
    )

    if score >= 75:

        signal = "STRONG BUY"
        direction = "UP"

    elif score >= 60:

        signal = "BUY"
        direction = "UP"

    elif score > 40:

        signal = "HOLD"
        direction = "FLAT"

    elif score >= 25:

        signal = "SELL"
        direction = "DOWN"

    else:

        signal = "STRONG SELL"
        direction = "DOWN"

    signal_strength = round(

        min(
            abs(
                score - 50
            )
            *
            2,

            100
        ),

        2
    )

    return {
        "score":
        score,

        "market_score":
        score,

        "signal":
        signal,

        "direction":
        direction,

        "signal_strength":
        signal_strength,

        # compatibility alias only
        "strength":
        signal_strength,

        "reasons":
        reasons
    }


def calculate_score(
    df,
    strategy=None
):

    if (
        df is None
        or
        len(df) < 2
    ):

        return _neutral_result(
            "Not enough market data"
        )

    current = df.iloc[
        -1
    ]

    previous = df.iloc[
        -2
    ]

    return calculate_market_score(
        current,
        previous,
        strategy
    )