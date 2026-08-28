import numpy as np


def calculate_max_drawdown(
        balance_history
):

    if not balance_history:

        return 0.0


    peak = float(
        balance_history[0]
    )


    if peak <= 0:

        return 0.0


    max_drawdown = 0.0


    for value in balance_history:


        value = float(
            value
        )


        if value > peak:

            peak = value


        if peak <= 0:

            continue


        drawdown = (

            peak
            -
            value

        ) / peak


        if drawdown > max_drawdown:

            max_drawdown = drawdown


    return round(
        max_drawdown * 100,
        2
    )



def calculate_sharpe_ratio(
        returns
):

    if not returns:

        return 0.0


    returns = np.array(
        returns,
        dtype=float
    )


    if len(returns) == 0:

        return 0.0


    mean_return = np.mean(
        returns
    )


    volatility = np.std(
        returns
    )


    if volatility == 0:

        return 0.0


    sharpe = (

        mean_return

        /

        volatility

    )


    return round(
        float(sharpe),
        2
    )



def calculate_volatility(
        returns
):

    if not returns:

        return 0.0


    returns = np.array(
        returns,
        dtype=float
    )


    if len(returns) == 0:

        return 0.0


    volatility = np.std(
        returns
    )


    return round(
        float(
            volatility
            *
            100
        ),
        2
    )



def _get_completed_trades(
        strategy
):

    if not isinstance(
        strategy,
        dict
    ):

        return []


    history = strategy.get(
        "history",
        []
    )


    if not isinstance(
        history,
        list
    ):

        return []


    completed = []


    for trade in history:


        if not isinstance(
            trade,
            dict
        ):

            continue


        if trade.get(
            "type"
        ) not in [
            "SELL",
            "COVER"
        ]:

            continue


        if "profit" not in trade:

            continue


        completed.append(
            trade
        )


    return completed



def generate_risk_report(
        strategy,
        monte=None
):

    print(
        "\n🛡️ Risk Analysis Running..."
    )


    completed_trades = (
        _get_completed_trades(
            strategy
        )
    )


    # =========================
    # NO OOS TRADES
    # =========================
    #
    # Do not label zero observations
    # as LOW risk.

    if not completed_trades:


        return {

            "max_drawdown":
            0.0,


            "sharpe_ratio":
            0.0,


            "volatility":
            0.0,


            "risk_score":
            None,


            "risk_level":
            "HIGH",


            "trade_count":
            0,


            "status":
            "insufficient_data",


            "strategy":
            strategy,


            "monte_carlo":
            monte

        }



    # =========================
    # BUILD EQUITY CURVE
    # =========================


    initial_balance = 1000.0


    balance = initial_balance


    balance_history = [
        balance
    ]


    returns = []



    for trade in completed_trades:


        profit = float(
            trade.get(
                "profit",
                0
            )
        )


        balance += profit


        balance_history.append(
            balance
        )



        # Engine's "return" field is
        # NET percentage after fees.

        if "return" in trade:


            trade_return = (

                float(
                    trade.get(
                        "return",
                        0
                    )
                )

                /

                100

            )


        else:


            # Fallback only for old records.
            # Approximate relative to the
            # fixed $100 trade amount used
            # by the current backtest.

            trade_return = (

                profit

                /

                100.0

            )


        returns.append(
            trade_return
        )



    # =========================
    # RISK METRICS
    # =========================


    drawdown = (
        calculate_max_drawdown(
            balance_history
        )
    )


    sharpe = (
        calculate_sharpe_ratio(
            returns
        )
    )


    volatility = (
        calculate_volatility(
            returns
        )
    )



    # =========================
    # RISK SCORE
    # =========================


    risk_score = 0



    # Drawdown risk

    if drawdown > 20:

        risk_score += 40


    elif drawdown > 10:

        risk_score += 25


    else:

        risk_score += 10



    # Volatility risk

    if volatility > 5:

        risk_score += 30


    elif volatility > 2:

        risk_score += 20


    else:

        risk_score += 10



    # Sharpe quality

    if sharpe < 0:

        risk_score += 30


    elif sharpe < 1:

        risk_score += 20


    else:

        risk_score += 5



    if risk_score <= 30:

        level = "LOW"


    elif risk_score <= 60:

        level = "MEDIUM"


    else:

        level = "HIGH"



    report = {

        "max_drawdown":
        drawdown,


        "sharpe_ratio":
        sharpe,


        "volatility":
        volatility,


        "risk_score":
        risk_score,


        "risk_level":
        level,


        "trade_count":
        len(
            completed_trades
        ),


        "status":
        "completed",


        "strategy":
        strategy,


        "monte_carlo":
        monte

    }



    print(
        "OOS Trades:",
        report[
            "trade_count"
        ]
    )


    print(
        "Max Drawdown:",
        drawdown,
        "%"
    )


    print(
        "Sharpe Ratio:",
        sharpe
    )


    print(
        "Volatility:",
        volatility,
        "%"
    )


    print(
        "Risk Score:",
        risk_score
    )


    print(
        "Risk Level:",
        level
    )


    return report