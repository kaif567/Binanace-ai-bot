from strategy.scoring import calculate_market_score


def _validate_parameters(
    initial_balance,
    trade_amount,
    stop_loss,
    take_profit,
    fee
):
    if initial_balance <= 0:
        raise ValueError("initial_balance must be greater than 0")

    if trade_amount <= 0:
        raise ValueError("trade_amount must be greater than 0")

    if stop_loss <= 0:
        raise ValueError("stop_loss must be greater than 0")

    if take_profit <= 0:
        raise ValueError("take_profit must be greater than 0")

    if fee < 0:
        raise ValueError("fee cannot be negative")


def _get_time_value(row):
    try:
        if "time" in row.index:
            return int(row["time"])
    except Exception:
        pass

    return None


def _check_long_exit(
    candle,
    entry_price,
    stop_loss,
    take_profit
):
    candle_open = float(candle["open"])
    candle_high = float(candle["high"])
    candle_low = float(candle["low"])

    stop_price = entry_price * (1 - stop_loss)
    target_price = entry_price * (1 + take_profit)

    # Adverse gap
    if candle_open <= stop_price:
        return {
            "exit_price": candle_open,
            "exit_reason": "STOP_LOSS_GAP",
            "stop_price": stop_price,
            "target_price": target_price
        }

    # Favorable gap.
    # Strict > protects against exact-touch illusion.
    if candle_open > target_price:
        return {
            "exit_price": target_price,
            "exit_reason": "TAKE_PROFIT_GAP",
            "stop_price": stop_price,
            "target_price": target_price
        }

    stop_hit = candle_low <= stop_price

    # Strict TP inequality
    target_hit = candle_high > target_price

    # Conservative same-candle rule: SL first
    if stop_hit:
        return {
            "exit_price": stop_price,
            "exit_reason": "STOP_LOSS",
            "stop_price": stop_price,
            "target_price": target_price
        }

    if target_hit:
        return {
            "exit_price": target_price,
            "exit_reason": "TAKE_PROFIT",
            "stop_price": stop_price,
            "target_price": target_price
        }

    return None


def _check_short_exit(
    candle,
    entry_price,
    stop_loss,
    take_profit
):
    candle_open = float(candle["open"])
    candle_high = float(candle["high"])
    candle_low = float(candle["low"])

    stop_price = entry_price * (1 + stop_loss)
    target_price = entry_price * (1 - take_profit)

    # Adverse gap
    if candle_open >= stop_price:
        return {
            "exit_price": candle_open,
            "exit_reason": "STOP_LOSS_GAP",
            "stop_price": stop_price,
            "target_price": target_price
        }

    # Favorable gap.
    # Strict < protects against exact-touch illusion.
    if candle_open < target_price:
        return {
            "exit_price": target_price,
            "exit_reason": "TAKE_PROFIT_GAP",
            "stop_price": stop_price,
            "target_price": target_price
        }

    stop_hit = candle_high >= stop_price

    # Strict TP inequality
    target_hit = candle_low < target_price

    # Conservative same-candle rule: SL first
    if stop_hit:
        return {
            "exit_price": stop_price,
            "exit_reason": "STOP_LOSS",
            "stop_price": stop_price,
            "target_price": target_price
        }

    if target_hit:
        return {
            "exit_price": target_price,
            "exit_reason": "TAKE_PROFIT",
            "stop_price": stop_price,
            "target_price": target_price
        }

    return None


def _build_exit_trade(
    position,
    entry_price,
    exit_price,
    trade_amount,
    entry_fee,
    exit_fee,
    exit_reason,
    stop_price,
    target_price,
    candle
):
    if position == "LONG":
        gross_return = (
            exit_price - entry_price
        ) / entry_price

        trade_type = "SELL"

    else:
        gross_return = (
            entry_price - exit_price
        ) / entry_price

        trade_type = "COVER"

    gross_profit = trade_amount * gross_return

    total_fee = entry_fee + exit_fee

    net_profit = gross_profit - total_fee

    net_return = (
        net_profit / trade_amount
    ) * 100

    return {
        "type": trade_type,
        "position": position,

        "entry_price": round(entry_price, 8),
        "exit_price": round(exit_price, 8),
        "price": round(exit_price, 8),

        "stop_price": round(stop_price, 8),
        "target_price": round(target_price, 8),

        "exit_reason": exit_reason,

        "gross_profit": round(gross_profit, 8),

        "entry_fee": round(entry_fee, 8),
        "exit_fee": round(exit_fee, 8),
        "fee_cost": round(total_fee, 8),

        # NET after both fees
        "profit": round(net_profit, 8),

        "gross_return": round(
            gross_return * 100,
            6
        ),

        # NET return
        "return": round(
            net_return,
            6
        ),

        "exit_time": _get_time_value(
            candle
        )
    }


def _force_close_at_boundary(
    position,
    entry_price,
    trade_amount,
    entry_fee,
    fee,
    candle,
    stop_loss,
    take_profit
):
    """
    Walk-forward fold boundary rule.

    Any still-open position is marked to market
    using the final candle CLOSE.

    This prevents cross-fold open trades from
    disappearing from OOS PnL.
    """

    exit_price = float(
        candle["close"]
    )

    exit_fee = (
        trade_amount * fee
    )

    if position == "LONG":
        stop_price = (
            entry_price
            *
            (1 - stop_loss)
        )

        target_price = (
            entry_price
            *
            (1 + take_profit)
        )

    else:
        stop_price = (
            entry_price
            *
            (1 + stop_loss)
        )

        target_price = (
            entry_price
            *
            (1 - take_profit)
        )

    return _build_exit_trade(
        position=position,
        entry_price=entry_price,
        exit_price=exit_price,
        trade_amount=trade_amount,
        entry_fee=entry_fee,
        exit_fee=exit_fee,
        exit_reason="FOLD_END_MTM",
        stop_price=stop_price,
        target_price=target_price,
        candle=candle
    )


def _empty_result(
    initial_balance,
    strategy
):
    return {
        "initial": initial_balance,
        "final": initial_balance,
        "profit": 0,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "history": [],
        "sample_quality": "LOW_SAMPLE_SIZE",
        "open_position": None,
        "pending_entry": None,
        "strategy": strategy if strategy else {}
    }


def run_advanced_backtest(
    df,
    initial_balance=1000,
    trade_amount=100,
    stop_loss=0.02,
    take_profit=0.05,
    donchian_period=20,
    fee=0.001,
    strategy=None,
    trade_start_index=1,
    force_close_at_end=False
):
    """
    Realistic backtest execution.

    Important rules:
    - Signal generated on CLOSED candle.
    - Entry happens on NEXT candle OPEN.
    - TP/SL use high/low.
    - Exact TP touch does not guarantee fill.
    - Same candle TP + SL => SL first.
    - Adverse gap => actual OPEN.
    - Favorable gap => conservative TP price.
    - Entry + exit fee both charged.
    - Walk-forward can restrict trading to OOS
      via trade_start_index.
    - Open OOS trade can be MTM closed at fold end.
    """

    _validate_parameters(
        initial_balance,
        trade_amount,
        stop_loss,
        take_profit,
        fee
    )

    if df is None:
        raise ValueError(
            "df cannot be None"
        )

    if len(df) < 3:
        return _empty_result(
            initial_balance,
            strategy
        )

    required_columns = [
        "open",
        "high",
        "low",
        "close"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Missing required column: {column}"
            )

    trade_start_index = int(
        trade_start_index
    )

    if trade_start_index < 1:
        trade_start_index = 1

    if trade_start_index >= len(df):
        raise ValueError(
            "trade_start_index must be inside dataframe"
        )

    balance = float(
        initial_balance
    )

    position = None
    entry_price = None
    entry_fee = 0.0

    pending_entry = None

    trades = []

    for i in range(
        1,
        len(df)
    ):
        current = df.iloc[i]

        previous = df.iloc[
            i - 1
        ]

        # ==================================
        # EXECUTE PREVIOUS SIGNAL AT OPEN
        # ==================================

        if (
            i >= trade_start_index
            and
            position is None
            and
            pending_entry is not None
        ):
            position = pending_entry[
                "position"
            ]

            entry_price = float(
                current["open"]
            )

            entry_fee = (
                trade_amount
                *
                fee
            )

            balance -= entry_fee

            if position == "LONG":
                trade_type = "BUY"
            else:
                trade_type = "SHORT"

            trades.append({
                "type": trade_type,
                "position": position,

                "price": round(
                    entry_price,
                    8
                ),

                "entry_price": round(
                    entry_price,
                    8
                ),

                "entry_fee": round(
                    entry_fee,
                    8
                ),

                "entry_time":
                _get_time_value(
                    current
                ),

                "entry_index": i,

                "signal_index":
                pending_entry[
                    "signal_index"
                ],

                "signal_time":
                pending_entry[
                    "signal_time"
                ],

                "signal_close_price":
                pending_entry[
                    "signal_close_price"
                ],

                "score":
                pending_entry[
                    "score"
                ],

                "signal":
                pending_entry[
                    "signal"
                ],

                "reasons":
                pending_entry[
                    "reasons"
                ]
            })

            pending_entry = None

        # ==================================
        # CHECK OPEN POSITION EXIT
        # ==================================

        if (
            i >= trade_start_index
            and
            position is not None
        ):
            if position == "LONG":
                exit_data = _check_long_exit(
                    current,
                    entry_price,
                    stop_loss,
                    take_profit
                )

            else:
                exit_data = _check_short_exit(
                    current,
                    entry_price,
                    stop_loss,
                    take_profit
                )

            if exit_data is not None:
                exit_price = float(
                    exit_data[
                        "exit_price"
                    ]
                )

                exit_fee = (
                    trade_amount
                    *
                    fee
                )

                exit_trade = _build_exit_trade(
                    position=position,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    trade_amount=trade_amount,
                    entry_fee=entry_fee,
                    exit_fee=exit_fee,
                    exit_reason=exit_data[
                        "exit_reason"
                    ],
                    stop_price=exit_data[
                        "stop_price"
                    ],
                    target_price=exit_data[
                        "target_price"
                    ],
                    candle=current
                )

                # Entry fee already removed.
                balance += (
                    exit_trade[
                        "gross_profit"
                    ]
                    -
                    exit_fee
                )

                trades.append(
                    exit_trade
                )

                position = None
                entry_price = None
                entry_fee = 0.0

        # ==================================
        # GENERATE SIGNAL AT CANDLE CLOSE
        # ==================================

        signal_allowed = (
            position is None
            and
            pending_entry is None

            # no next bar => cannot execute
            and
            i < len(df) - 1

            # For OOS:
            # allow final training candle to
            # generate first OOS entry.
            and
            i >= trade_start_index - 1
        )

        if signal_allowed:
            explicit_signal = None

            if "signal" in current.index:
                candle_signal = current["signal"]

                if candle_signal in [
                    "STRONG BUY",
                    "STRONG SELL"
                ]:
                    explicit_signal = candle_signal

            if explicit_signal is not None:
                analysis = {
                    "score": 50,
                    "signal": explicit_signal,
                    "reasons": [
                        "Explicit candle signal"
                    ]
                }

            else:
                analysis = calculate_market_score(
                    current,
                    previous,
                    strategy,
                    donchian_period=donchian_period
                )

            score = float(
                analysis.get(
                    "score",
                    50
                )
            )

            signal = analysis.get(
                "signal",
                "HOLD"
            )

            reasons = analysis.get(
                "reasons",
                []
            )

            if signal == "STRONG BUY":
                pending_entry = {
                    "position": "LONG",
                    "score": score,
                    "signal": signal,
                    "reasons": reasons,

                    "signal_index": i,

                    "signal_time":
                    _get_time_value(
                        current
                    ),

                    "signal_close_price":
                    float(
                        current["close"]
                    )
                }

            elif signal == "STRONG SELL":
                pending_entry = {
                    "position": "SHORT",
                    "score": score,
                    "signal": signal,
                    "reasons": reasons,

                    "signal_index": i,

                    "signal_time":
                    _get_time_value(
                        current
                    ),

                    "signal_close_price":
                    float(
                        current["close"]
                    )
                }

    # ==================================
    # WALK-FORWARD BOUNDARY MTM
    # ==================================

    if (
        force_close_at_end
        and
        position is not None
    ):
        final_candle = df.iloc[
            -1
        ]

        exit_trade = (
            _force_close_at_boundary(
                position=position,
                entry_price=entry_price,
                trade_amount=trade_amount,
                entry_fee=entry_fee,
                fee=fee,
                candle=final_candle,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
        )

        exit_fee = float(
            exit_trade[
                "exit_fee"
            ]
        )

        balance += (
            exit_trade[
                "gross_profit"
            ]
            -
            exit_fee
        )

        trades.append(
            exit_trade
        )

        position = None
        entry_price = None
        entry_fee = 0.0

    # ==================================
    # PERFORMANCE
    # ==================================

    closed_trades = [
        trade
        for trade in trades
        if trade.get(
            "type"
        ) in [
            "SELL",
            "COVER"
        ]
    ]

    profits = [
        float(
            trade.get(
                "profit",
                0
            )
        )
        for trade in closed_trades
    ]

    wins = len([
        value
        for value in profits
        if value > 0
    ])

    losses = (
        len(profits)
        -
        wins
    )

    total = len(
        profits
    )

    if total > 0:
        win_rate = (
            wins
            /
            total
        ) * 100
    else:
        win_rate = 0

    gross_profit = sum(
        value
        for value in profits
        if value > 0
    )

    gross_loss = abs(
        sum(
            value
            for value in profits
            if value < 0
        )
    )

    if gross_loss > 0:
        profit_factor = (
            gross_profit
            /
            gross_loss
        )

    elif gross_profit > 0:
        # Keep downstream behavior finite.
        profit_factor = (
            gross_profit
        )

    else:
        profit_factor = 0

    if total >= 50:
        sample_quality = "GOOD"

    elif total >= 20:
        sample_quality = "MEDIUM"

    else:
        sample_quality = (
            "LOW_SAMPLE_SIZE"
        )

    return {
        "initial":
        initial_balance,

        "final":
        round(
            balance,
            8
        ),

        "profit":
        round(
            balance
            -
            initial_balance,
            8
        ),

        "trades":
        total,

        "wins":
        wins,

        "losses":
        losses,

        "win_rate":
        round(
            win_rate,
            2
        ),

        "profit_factor":
        round(
            profit_factor,
            4
        ),

        "history":
        trades,

        "sample_quality":
        sample_quality,

        "open_position":
        position,

        "pending_entry":
        pending_entry,

        "strategy":
        strategy if strategy else {}
    }