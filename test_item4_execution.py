import pandas as pd

import backtest.engine as engine


ORIGINAL_SCORER = (
    engine.calculate_market_score
)


def fake_market_score(
        current,
        previous,
        strategy=None
):

    signal = current.get(
        "test_signal",
        "HOLD"
    )

    if signal == "STRONG BUY":

        score = 90

    elif signal == "STRONG SELL":

        score = 10

    else:

        score = 50

    return {

        "score":
        score,

        "signal":
        signal,

        "reasons":
        [
            "CONTROLLED TEST"
        ]
    }


def build_df(
        rows
):

    prepared = []

    for index, row in enumerate(
        rows
    ):

        item = {

            "time":
            index,

            "open":
            row["open"],

            "high":
            row["high"],

            "low":
            row["low"],

            "close":
            row["close"],

            "test_signal":
            row.get(
                "signal",
                "HOLD"
            )
        }

        prepared.append(
            item
        )

    return pd.DataFrame(
        prepared
    )


def run_case(
        rows,
        stop_loss=0.02,
        take_profit=0.05
):

    df = build_df(
        rows
    )

    return engine.run_advanced_backtest(

        df,

        initial_balance=1000,

        trade_amount=100,

        stop_loss=stop_loss,

        take_profit=take_profit,

        fee=0.001

    )


def get_entries(
        result
):

    return [

        trade

        for trade in result[
            "history"
        ]

        if trade.get(
            "type"
        ) in [
            "BUY",
            "SHORT"
        ]
    ]


def get_exits(
        result
):

    return [

        trade

        for trade in result[
            "history"
        ]

        if trade.get(
            "type"
        ) in [
            "SELL",
            "COVER"
        ]
    ]


def expect(
        condition,
        message
):

    if not condition:

        raise AssertionError(
            message
        )


def expect_close(
        actual,
        expected,
        tolerance=0.000001
):

    if abs(
        float(actual)
        -
        float(expected)
    ) > tolerance:

        raise AssertionError(
            f"Expected {expected}, got {actual}"
        )


def test_next_open_entry():

    result = run_case([

        {
            "open": 90,
            "high": 92,
            "low": 89,
            "close": 91
        },

        {
            "open": 91,
            "high": 93,
            "low": 90,
            "close": 92,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        }
    ])

    entries = get_entries(
        result
    )

    expect(
        len(entries) == 1,
        "Expected one entry"
    )

    expect_close(
        entries[0][
            "signal_close_price"
        ],
        92
    )

    expect_close(
        entries[0][
            "entry_price"
        ],
        100
    )

    print(
        "NEXT OPEN ENTRY: PASS ✅"
    )


def test_long_tp():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 106,
            "low": 99,
            "close": 104
        }
    ])

    exits = get_exits(
        result
    )

    expect(
        len(exits) == 1,
        "Expected LONG TP exit"
    )

    trade = exits[0]

    expect(
        trade["exit_reason"]
        ==
        "TAKE_PROFIT",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        105
    )

    # 5% gross profit = $5
    # round-trip fees = $0.20
    # net = $4.80

    expect_close(
        trade[
            "gross_profit"
        ],
        5
    )

    expect_close(
        trade[
            "fee_cost"
        ],
        0.2
    )

    expect_close(
        trade[
            "profit"
        ],
        4.8
    )

    print(
        "LONG TP + ROUND-TRIP FEES: PASS ✅"
    )


def test_long_exact_tp_touch():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 104
        }
    ])

    exits = get_exits(
        result
    )

    expect(
        len(exits) == 0,
        "Exact LONG TP touch incorrectly filled"
    )

    print(
        "LONG EXACT TP TOUCH: PASS ✅"
    )


def test_long_sl():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 104,
            "low": 97,
            "close": 99
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "STOP_LOSS",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        98
    )

    print(
        "LONG SL: PASS ✅"
    )


def test_long_conflict():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 106,
            "low": 97,
            "close": 101
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "STOP_LOSS",
        "Same-candle conflict must choose SL"
    )

    print(
        "LONG TP+SL CONFLICT → SL: PASS ✅"
    )


def test_long_adverse_gap():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 103,
            "low": 99,
            "close": 101
        },

        {
            "open": 97,
            "high": 99,
            "low": 96,
            "close": 98
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "STOP_LOSS_GAP",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        97
    )

    print(
        "LONG ADVERSE GAP: PASS ✅"
    )


def test_long_favorable_gap():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG BUY"
        },

        {
            "open": 100,
            "high": 103,
            "low": 99,
            "close": 101
        },

        {
            "open": 106,
            "high": 108,
            "low": 105,
            "close": 107
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "TAKE_PROFIT_GAP",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        105
    )

    print(
        "LONG FAVORABLE GAP CONSERVATIVE TP: PASS ✅"
    )


def test_short_tp():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG SELL"
        },

        {
            "open": 100,
            "high": 101,
            "low": 94,
            "close": 96
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "TAKE_PROFIT",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        95
    )

    print(
        "SHORT TP: PASS ✅"
    )


def test_short_exact_tp_touch():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG SELL"
        },

        {
            "open": 100,
            "high": 101,
            "low": 95,
            "close": 96
        }
    ])

    exits = get_exits(
        result
    )

    expect(
        len(exits) == 0,
        "Exact SHORT TP touch incorrectly filled"
    )

    print(
        "SHORT EXACT TP TOUCH: PASS ✅"
    )


def test_short_sl():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG SELL"
        },

        {
            "open": 100,
            "high": 103,
            "low": 96,
            "close": 101
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "STOP_LOSS",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        102
    )

    print(
        "SHORT SL: PASS ✅"
    )


def test_short_conflict():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG SELL"
        },

        {
            "open": 100,
            "high": 103,
            "low": 94,
            "close": 99
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "STOP_LOSS",
        "SHORT conflict must choose SL"
    )

    print(
        "SHORT TP+SL CONFLICT → SL: PASS ✅"
    )


def test_short_adverse_gap():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG SELL"
        },

        {
            "open": 100,
            "high": 101,
            "low": 97,
            "close": 99
        },

        {
            "open": 103,
            "high": 104,
            "low": 102,
            "close": 103
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "STOP_LOSS_GAP",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        103
    )

    print(
        "SHORT ADVERSE GAP: PASS ✅"
    )


def test_short_favorable_gap():

    result = run_case([

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100
        },

        {
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "signal": "STRONG SELL"
        },

        {
            "open": 100,
            "high": 101,
            "low": 97,
            "close": 99
        },

        {
            "open": 94,
            "high": 95,
            "low": 93,
            "close": 94
        }
    ])

    trade = get_exits(
        result
    )[0]

    expect(
        trade["exit_reason"]
        ==
        "TAKE_PROFIT_GAP",
        trade
    )

    expect_close(
        trade[
            "exit_price"
        ],
        95
    )

    print(
        "SHORT FAVORABLE GAP CONSERVATIVE TP: PASS ✅"
    )


def main():

    print(
        "======================================"
    )

    print(
        "ITEM 4 EXECUTION CONTROLLED TEST"
    )

    print(
        "======================================"
    )

    engine.calculate_market_score = (
        fake_market_score
    )

    try:

        test_next_open_entry()

        test_long_tp()

        test_long_exact_tp_touch()

        test_long_sl()

        test_long_conflict()

        test_long_adverse_gap()

        test_long_favorable_gap()

        test_short_tp()

        test_short_exact_tp_touch()

        test_short_sl()

        test_short_conflict()

        test_short_adverse_gap()

        test_short_favorable_gap()

        print(
            "\n======================================"
        )

        print(
            "ITEM 4 CONTROLLED TEST: PASS ✅"
        )

        print(
            "======================================"
        )

    finally:

        engine.calculate_market_score = (
            ORIGINAL_SCORER
        )


if __name__ == "__main__":

    main()