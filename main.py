from monitor.live_monitor import (
    start_live_monitor
)


SYMBOL = "BTCUSDT"


# ==============================
# DATA / WALK-FORWARD
# ==============================

HISTORICAL_CANDLES = 3000

INITIAL_TRAIN_WINDOW = 1500

TEST_WINDOW = 200

STEP = 200

MIN_OOS_TRADES = 20


# ==============================
# POLLING
# ==============================

PRICE_POLL_INTERVAL = 10

CANDLE_POLL_INTERVAL = 60


RECENT_GAP_WINDOW_CANDLES = 24

HEAVY_RETRY_SECONDS = 300


# ==============================
# PAPER EXECUTION SAFETY
# ==============================
#
# Keep FALSE until the full live smoke
# test has passed.
#
# False:
#   real market data
#   real walk-forward
#   real metrics
#   NO new paper positions
#
# True:
#   eligible LONG/SHORT paper entries
#   are allowed.

PAPER_ENTRIES_ENABLED = True


def main():

    print(
        "=============================="
    )

    print(
        "🤖 BINANCE AI BOT START"
    )

    print(
        "=============================="
    )


    print(
        "\n📊 CONFIGURATION"
    )


    print(
        "Symbol:",
        SYMBOL
    )


    print(
        "Historical Candles:",
        HISTORICAL_CANDLES
    )


    print(
        "Walk Forward:",
        (
            f"{INITIAL_TRAIN_WINDOW}/"
            f"{TEST_WINDOW}/"
            f"{STEP}"
        )
    )


    print(
        "Live Price Poll:",
        PRICE_POLL_INTERVAL,
        "seconds"
    )


    print(
        "Closed Candle Light Poll:",
        CANDLE_POLL_INTERVAL,
        "seconds"
    )


    print(
        "Paper Entries Enabled:",
        PAPER_ENTRIES_ENABLED
    )


    if not PAPER_ENTRIES_ENABLED:

        print(
            "🛑 SAFE MODE: NEW PAPER ENTRIES DISABLED"
        )


    print(
        "\n✅ Starting monitor..."
    )


    start_live_monitor(

        symbol=
        SYMBOL,


        price_poll_interval=
        PRICE_POLL_INTERVAL,


        candle_poll_interval=
        CANDLE_POLL_INTERVAL,


        historical_candles=
        HISTORICAL_CANDLES,


        initial_train_window=
        INITIAL_TRAIN_WINDOW,


        test_window=
        TEST_WINDOW,


        step=
        STEP,


        min_oos_trades=
        MIN_OOS_TRADES,


        recent_gap_window_candles=
        RECENT_GAP_WINDOW_CANDLES,


        heavy_retry_seconds=
        HEAVY_RETRY_SECONDS,


        paper_entries_enabled=
        PAPER_ENTRIES_ENABLED

    )


if __name__ == "__main__":

    main()