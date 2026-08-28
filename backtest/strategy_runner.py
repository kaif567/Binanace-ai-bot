import pandas as pd



def apply_strategy_parameters(
        df,
        strategy
):


    data = df.copy()



    ema_values = (
        strategy["ema"]
        .split("/")
    )


    fast = int(
        ema_values[0]
    )


    slow = int(
        ema_values[1]
    )



    # Dynamic EMA


    data["ema_fast"] = (

        data["close"]

        .ewm(
            span=fast
        )

        .mean()

    )



    data["ema_slow"] = (

        data["close"]

        .ewm(
            span=slow
        )

        .mean()

    )



    # Dynamic parameters


    data.attrs["stop_loss"] = (
        strategy["sl"]
    )


    data.attrs["take_profit"] = (
        strategy["tp"]
    )



    data.attrs["strategy"] = strategy



    return data