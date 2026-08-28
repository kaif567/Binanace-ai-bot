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