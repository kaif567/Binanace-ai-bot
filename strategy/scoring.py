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
    strategy=None,
    donchian_period=20
):
    import pandas as pd
    close = float(current.get("close", 0))
    dh = float(current.get(f"donchian_high_{donchian_period}", 0))
    dl = float(current.get(f"donchian_low_{donchian_period}", 0))
    
    if pd.isna(dh) or pd.isna(dl) or dh == 0 or dl == 0:
        return {
            "score": 50,
            "market_score": 50,
            "signal": "HOLD",
            "direction": "FLAT",
            "strength": 0,
            "reasons": []
        }
        
    if close > dh:
        return {
            "score": 100,
            "market_score": 100,
            "signal": "STRONG BUY",
            "direction": "UP",
            "strength": 100,
            "reasons": ["Donchian High Breakout"]
        }
    elif close < dl:
        return {
            "score": 0,
            "market_score": 0,
            "signal": "STRONG SELL",
            "direction": "DOWN",
            "strength": 100,
            "reasons": ["Donchian Low Breakout"]
        }
    else:
        return {
            "score": 50,
            "market_score": 50,
            "signal": "HOLD",
            "direction": "FLAT",
            "strength": 0,
            "reasons": ["Inside Donchian Channel"]
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