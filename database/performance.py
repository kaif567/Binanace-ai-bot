from database import paper_store


PAPER_NOTIONAL = 100.0

DEFAULT_FEE_RATE = 0.001


def load_trades():

    return (
        paper_store.load_trades()
    )


def _is_legacy(
        trade
):

    return (
        int(
            trade.get(
                "schema_version",
                0
            )
            or
            0
        )
        <
        2
    )


def _calculate_open_position(
        position,
        current_price
):

    entry = float(
        position.get(
            "entry_price",
            0
        )
    )


    if entry <= 0:

        return {
            "status":
            "INVALID_ENTRY_PRICE"
        }


    if _is_legacy(
        position
    ):

        return {

            "status":
            "LEGACY_OPEN_POSITION",


            "entry_price":
            entry,


            "current_price":
            current_price,


            "message":
            (
                "Legacy position requires manual "
                "review before Item 8 trading."
            )

        }


    side = position.get(
        "side"
    )


    notional = float(
        position.get(
            "notional",
            PAPER_NOTIONAL
        )
    )


    fee_rate = float(
        position.get(
            "fee_rate",
            DEFAULT_FEE_RATE
        )
    )


    if side == "LONG":

        gross_return_decimal = (
            (
                current_price
                -
                entry
            )
            /
            entry
        )


    elif side == "SHORT":

        gross_return_decimal = (
            (
                entry
                -
                current_price
            )
            /
            entry
        )


    else:

        return {
            "status":
            "UNKNOWN_SIDE"
        }


    gross_profit = (
        gross_return_decimal
        *
        notional
    )


    estimated_entry_fee = float(
        position.get(
            "entry_fee",
            notional
            *
            fee_rate
        )
    )


    estimated_exit_fee = (
        notional
        *
        fee_rate
    )


    estimated_fee_cost = (
        estimated_entry_fee
        +
        estimated_exit_fee
    )


    estimated_net_profit = (
        gross_profit
        -
        estimated_fee_cost
    )


    estimated_net_return = (
        estimated_net_profit
        /
        notional
        *
        100
    )


    return {

        "status":
        position.get(
            "status"
        ),


        "side":
        side,


        "entry_price":
        entry,


        "current_price":
        current_price,


        "gross_unrealized_return":
        round(
            gross_return_decimal
            *
            100,
            4
        ),


        "estimated_fee_cost":
        round(
            estimated_fee_cost,
            4
        ),


        "net_unrealized_return":
        round(
            estimated_net_return,
            4
        ),


        "estimated_net_profit":
        round(
            estimated_net_profit,
            4
        ),


        "take_profit_price":
        position.get(
            "take_profit_price"
        ),


        "stop_loss_price":
        position.get(
            "stop_loss_price"
        ),


        "last_checked_time":
        position.get(
            "last_checked_time"
        )

    }


def generate_performance_report(
        current_price=None
):

    trades = (
        load_trades()
    )


    closed = [

        trade

        for trade in trades

        if trade.get(
            "status"
        )
        ==
        "CLOSED"

    ]


    blocking = [

        trade

        for trade in trades

        if trade.get(
            "status"
        )
        in {
            "OPEN",
            "STALE_RECOVERY_FAILED"
        }

    ]


    report = {}


    # =========================
    # OPEN POSITION
    # =========================

    if (
        blocking
        and
        current_price is not None
    ):

        position = (
            blocking[
                -1
            ]
        )


        if (
            position.get(
                "status"
            )
            ==
            "STALE_RECOVERY_FAILED"
        ):

            report[
                "open_position"
            ] = {

                "status":
                "STALE_RECOVERY_FAILED",

                "message":
                (
                    "Manual paper-position review "
                    "required."
                ),

                "position_id":
                position.get(
                    "position_id"
                ),

                "side":
                position.get(
                    "side"
                ),

                "entry_price":
                position.get(
                    "entry_price"
                )

            }


        else:

            report[
                "open_position"
            ] = (
                _calculate_open_position(

                    position,

                    float(
                        current_price
                    )

                )
            )


    if not closed:

        report.update({

            "total_trades":
            0,


            "closed_trades":
            0,


            "message":
            "No closed trades yet"

        })


        return report


    # =========================
    # CLOSED PERFORMANCE
    # =========================

    total = len(
        closed
    )


    wins = 0

    losses = 0


    total_return = 0.0

    total_profit = 0.0

    total_fees = 0.0


    long_trades = 0

    short_trades = 0


    best = None

    worst = None


    for trade in closed:

        result = float(
            trade.get(
                "return",
                0
            )
        )


        profit = float(
            trade.get(
                "profit",
                0
            )
        )


        fee_cost = float(
            trade.get(
                "fee_cost",
                0
            )
        )


        total_return += result

        total_profit += profit

        total_fees += fee_cost


        if (
            trade.get(
                "side"
            )
            ==
            "LONG"
        ):

            long_trades += 1


        elif (
            trade.get(
                "side"
            )
            ==
            "SHORT"
        ):

            short_trades += 1


        if result > 0:

            wins += 1

        else:

            losses += 1


        if (
            best is None
            or
            result > best
        ):

            best = result


        if (
            worst is None
            or
            result < worst
        ):

            worst = result


    win_rate = round(
        (
            wins
            /
            total
        )
        *
        100,
        2
    )


    report.update({

        "total_trades":
        total,


        "closed_trades":
        total,


        "long_trades":
        long_trades,


        "short_trades":
        short_trades,


        "wins":
        wins,


        "losses":
        losses,


        "win_rate":
        win_rate,


        "total_return":
        round(
            total_return,
            4
        ),


        "total_profit":
        round(
            total_profit,
            4
        ),


        "total_fees":
        round(
            total_fees,
            4
        ),


        "best_trade":
        best,


        "worst_trade":
        worst

    })


    return report


def print_performance(
        current_price=None
):

    report = (
        generate_performance_report(
            current_price
        )
    )


    print(
        "\n=============================="
    )

    print(
        "📊 PERFORMANCE REPORT"
    )

    print(
        "=============================="
    )


    for key, value in report.items():

        print(
            key,
            ":",
            value
        )