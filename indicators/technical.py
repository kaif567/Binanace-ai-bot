import ta


def add_indicators(df):

    # RSI

    df["rsi"] = ta.momentum.RSIIndicator(
        df["close"],
        window=14
    ).rsi()


    # EMA

    df["ema20"] = ta.trend.EMAIndicator(
        df["close"],
        window=20
    ).ema_indicator()


    df["ema50"] = ta.trend.EMAIndicator(
        df["close"],
        window=50
    ).ema_indicator()


    # MACD

    macd = ta.trend.MACD(
        df["close"]
    )

    df["macd"] = macd.macd()

    df["macd_signal"] = macd.macd_signal()


    # Bollinger Bands

    bb = ta.volatility.BollingerBands(
        df["close"],
        window=20
    )

    df["bb_high"] = bb.bollinger_hband()

    df["bb_low"] = bb.bollinger_lband()


    # ATR

    atr = ta.volatility.AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )

    df["atr"] = atr.average_true_range()

    # Donchian Channels
    df["donchian_high_20"] = df["high"].rolling(20).max().shift(1)
    df["donchian_low_20"] = df["low"].rolling(20).min().shift(1)


    # ADX

    adx = ta.trend.ADXIndicator(
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )

    df["adx"] = adx.adx()


    # Volume average

    df["volume_avg"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )


    return df



def get_trend(df):

    """
    Determine market trend using EMA20 and EMA50.

    Returns:
        BULLISH  -> EMA20 above EMA50
        BEARISH  -> EMA20 below EMA50
        SIDEWAYS -> insufficient data or equal EMA
    """

    if df is None or len(df) == 0:
        return "SIDEWAYS"


    if (
        "ema20" not in df.columns
        or
        "ema50" not in df.columns
    ):
        df = add_indicators(
            df.copy()
        )


    try:

        ema20 = df["ema20"].iloc[-1]

        ema50 = df["ema50"].iloc[-1]


        if (
            ema20 is None
            or
            ema50 is None
        ):
            return "SIDEWAYS"


        if ema20 > ema50:

            return "BULLISH"


        elif ema20 < ema50:

            return "BEARISH"


        return "SIDEWAYS"


    except Exception:

        return "SIDEWAYS"