import time


from database.ai_log import (
    save_ai_decision,
    evaluate_pending_predictions
)


from database.performance import (
    print_performance
)


from data.binance_api import (
    get_price,
    get_latest_closed_candle,
    get_closed_candles_paginated,
    RecentCandleGapError
)


from backtest.pipeline import (
    run_ai_pipeline
)


from monitor.paper_trader import (
    execute_paper_trade,
    manage_open_position
)


from indicators.technical import (
    add_indicators
)


from indicators.mtf import (
    get_4h_trend_from_df,
    check_mtf_confluence
)


class InsufficientContinuousHistoryError(
        Exception
):
    pass


class CandleProcessingState:

    def __init__(
        self,
        last_processed_time=None
    ):

        self.last_processed_time = (
            last_processed_time
        )

        self.transient_failed_time = None

        self.retry_after_monotonic = 0.0

        self.historical_blocked_time = None


    def should_process(
        self,
        latest_time,
        now_monotonic=None
    ):

        latest_time = int(
            latest_time
        )


        if now_monotonic is None:

            now_monotonic = (
                time.monotonic()
            )


        if (
            self.last_processed_time
            is not None
            and
            latest_time
            <=
            self.last_processed_time
        ):

            return False


        if (
            self.historical_blocked_time
            ==
            latest_time
        ):

            return False


        if (
            self.transient_failed_time
            ==
            latest_time
            and
            now_monotonic
            <
            self.retry_after_monotonic
        ):

            return False


        return True


    def mark_success(
        self,
        processed_time
    ):

        self.last_processed_time = int(
            processed_time
        )

        self.transient_failed_time = None

        self.retry_after_monotonic = 0.0

        self.historical_blocked_time = None


    def mark_transient_failure(
        self,
        candle_time,
        retry_seconds=300,
        now_monotonic=None
    ):

        if now_monotonic is None:

            now_monotonic = (
                time.monotonic()
            )


        self.transient_failed_time = int(
            candle_time
        )


        self.retry_after_monotonic = (
            now_monotonic
            +
            float(
                retry_seconds
            )
        )


    def mark_historical_block(
        self,
        candle_time
    ):

        self.historical_blocked_time = int(
            candle_time
        )


def _manage_open_position(
        symbol,
        current_price
):

    result = (
        manage_open_position(

            current_price=
            current_price,

            symbol=
            symbol

        )
    )


    event = result.get(
        "event"
    )


    if event == "CLOSED":

        print(
            "\n📉 PAPER POSITION CLOSED"
        )

        print(
            result.get(
                "position"
            )
        )


    elif event == "LEGACY_OPEN_POSITION":

        print(
            "\n⚠️ LEGACY PAPER POSITION"
        )

        print(
            "Manual review required."
        )

        print(
            "New paper trades remain blocked."
        )


    elif event == "STALE_RECOVERY_FAILED":

        print(
            "\n⚠️ STALE PAPER POSITION"
        )

        print(
            (
                "Offline recovery exceeded safety "
                "limit. Manual review required."
            )
        )


    elif event == "RECOVERY_ERROR":

        print(
            "\n⚠️ PAPER RECOVERY ERROR:"
        )

        print(
            result.get(
                "error"
            )
        )


    return result


def handle_paper_entry(
        symbol,
        direction,
        paper_eligible,
        paper_reason,
        strategy,
        strategy_quality,
        signal_strength,
        directional_probability,
        probability_sample,
        current_price,
        signal_atr,
        paper_entries_enabled
):

    direction = str(
        direction
    ).upper()


    if direction == "FLAT":

        print(
            "\n⏸ HOLD / NO DIRECTION"
        )


        return {
            "event":
            "NO_DIRECTION"
        }


    if not paper_eligible:

        print(
            "\n⚠️ PAPER TRADE BLOCKED"
        )

        print(
            paper_reason
        )


        return {

            "event":
            "BLOCKED",

            "reason":
            paper_reason

        }


    if direction not in {
        "UP",
        "DOWN"
    }:

        return {

            "event":
            "BLOCKED",

            "reason":
            "Unsupported direction"

        }


    if current_price is None:

        return {

            "event":
            "BLOCKED",

            "reason":
            "Live price unavailable"

        }


    # =========================
    # PAPER ENTRY KILL SWITCH
    # =========================

    if not paper_entries_enabled:

        print(
            "\n🛑 PAPER ENTRY SUPPRESSED"
        )

        print(
            "Safe smoke mode is enabled."
        )

        print(
            "Eligible Direction:",
            direction
        )


        return {

            "event":
            "SUPPRESSED",

            "direction":
            direction

        }


    if direction == "UP":

        print(
            "\n🚀 PAPER LONG ELIGIBLE"
        )


    else:

        print(
            "\n🔻 PAPER SHORT ELIGIBLE"
        )


    trade = (
        execute_paper_trade({

            "symbol":
            symbol,


            "direction":
            direction,


            "best_strategy":
            strategy,


            "strategy_quality":
            strategy_quality,


            "signal_strength":
            signal_strength,


            "directional_probability":
            directional_probability,


            "directional_probability_sample":
            probability_sample,


            "price":
            current_price,


            "atr":
            signal_atr

        })
    )


    print(
        "TRADE:",
        trade
    )


    return {

        "event":
        "EXECUTED",

        "trade":
        trade

    }


def _print_integrity_report(
        report
):

    print(
        "\n=============================="
    )

    print(
        "🧹 HISTORICAL DATA INTEGRITY"
    )

    print(
        "=============================="
    )


    print(
        "Requested:",
        report.get(
            "requested_limit"
        )
    )


    print(
        "Returned:",
        report.get(
            "returned_rows"
        )
    )


    print(
        "Pages:",
        report.get(
            "pages"
        )
    )


    print(
        "Pagination Duplicates Removed:",
        report.get(
            "pagination_duplicates_removed",
            0
        )
    )


    print(
        "Historical Gaps:",
        report.get(
            "historical_gap_count",
            0
        )
    )


    print(
        "Recent Gaps:",
        report.get(
            "recent_gap_count",
            0
        )
    )


    print(
        "Historical Rows Truncated:",
        report.get(
            "truncated_rows",
            0
        )
    )


def _run_heavy_cycle(
        symbol,
        historical_candles,
        initial_train_window,
        test_window,
        step,
        min_oos_trades,
        recent_gap_window_candles,
        current_price=None,
        paper_entries_enabled=False
):

    print(
        "\n================================"
    )

    print(
        "🏋️ HEAVY HOURLY PIPELINE START"
    )

    print(
        "================================"
    )


    df, integrity = (
        get_closed_candles_paginated(

            symbol,

            interval="1h",

            limit=
            historical_candles,

            recent_gap_window_candles=
            recent_gap_window_candles,

            truncate_historical_gaps=True,

            return_report=True

        )
    )


    _print_integrity_report(
        integrity
    )


    minimum_required = (
        int(
            initial_train_window
        )
        +
        int(
            test_window
        )
    )


    if len(
        df
    ) < minimum_required:

        raise (
            InsufficientContinuousHistoryError(

                (
                    "Most recent continuous history "
                    f"contains {len(df)} candles, "
                    f"but at least {minimum_required} "
                    "are required."
                )

            )
        )


    df = (
        add_indicators(
            df
        )
    )


    signal_candle = (
        df.iloc[
            -1
        ]
    )


    signal_candle_open_time = int(
        signal_candle[
            "time"
        ]
    )


    signal_close_price = float(
        signal_candle[
            "close"
        ]
    )


    signal_atr = float(
        signal_candle[
            "atr"
        ]
    )


    evaluate_pending_predictions(
        df
    )


    try:
        print("\nFetching 4h candles for MTF Confluence check...")
        df_4h, _ = get_closed_candles_paginated(
            symbol,
            interval="4h",
            limit=200,
            page_size=200
        )
        df_4h = add_indicators(df_4h)
        htf_trend = get_4h_trend_from_df(df_4h)
    except Exception as e:
        print(f"Warning: Failed to fetch 4h data for MTF check: {e}")
        htf_trend = "SIDEWAYS"


    result = (
        run_ai_pipeline(

            df,

            symbol,

            initial_train_window=
            initial_train_window,

            test_window=
            test_window,

            step=
            step,

            min_oos_trades=
            min_oos_trades,

            htf_trend=htf_trend

        )
    )


    strategy = result.get(
        "best_strategy",
        {}
    )


    market_signal = result.get(
        "market_signal",
        "HOLD"
    )


    direction = result.get(
        "direction",
        "FLAT"
    )


    market_score = float(
        result.get(
            "market_score",
            50
        )
    )


    strategy_quality = float(
        result.get(
            "strategy_quality",
            0
        )
    )


    signal_strength = float(
        result.get(
            "signal_strength",
            0
        )
    )


    directional_probability = (
        result.get(
            "directional_probability"
        )
    )


    probability_sample = int(
        result.get(
            "directional_probability_sample",
            0
        )
    )


    paper_eligible = bool(
        result.get(
            "paper_eligible",
            False
        )
    )


    paper_mode = result.get(
        "paper_mode",
        "BLOCKED"
    )


    paper_reason = result.get(
        "paper_reason",
        ""
    )


    # Phase 1 Chop Filter — read back from pipeline result
    # (pipeline computes this via classify_regime internally)
    regime_status = result.get(
        "regime_status",
        "UNKNOWN"
    )


    mtf_confluence = result.get(
        "mtf_confluence",
        "UNKNOWN"
    )


    save_ai_decision(

        signal_close_price,

        strategy_quality,

        signal_strength,

        directional_probability,

        probability_sample,

        strategy,

        market_signal,

        direction,

        market_score,

        signal_candle_open_time,

        signal_atr

    )


    print(
        "\n=============================="
    )

    print(
        "🤖 HOURLY SEPARATED METRICS"
    )

    print(
        "=============================="
    )


    print(
        "Signal Candle Time:",
        signal_candle_open_time
    )


    print(
        "Signal Candle Close:",
        signal_close_price
    )


    print(
        "Strategy Quality:",
        strategy_quality
    )


    print(
        "Market Score:",
        market_score
    )


    print(
        "Signal Strength:",
        signal_strength
    )


    print(
        "Direction:",
        direction
    )


    print(
        "Directional Probability:",
        directional_probability
    )


    print(
        "Probability Sample:",
        probability_sample
    )


    print(
        "Paper Mode:",
        paper_mode
    )


    print(
        "Paper Eligible:",
        paper_eligible
    )


    print(
        "Reason:",
        paper_reason
    )


    print(
        "Regime Status:",
        regime_status
    )


    print(
        "HTF Trend (4h):",
        htf_trend
    )


    print(
        "MTF Confluence:",
        mtf_confluence
    )


    if current_price is None:

        try:

            current_price = float(
                get_price(
                    symbol
                )
            )

        except Exception as error:

            print(
                "Live Price Error:",
                error
            )

            current_price = None


    paper_entry_result = (
        handle_paper_entry(

            symbol=
            symbol,

            direction=
            direction,

            paper_eligible=
            paper_eligible,

            paper_reason=
            paper_reason,

            strategy=
            strategy,

            strategy_quality=
            strategy_quality,

            signal_strength=
            signal_strength,

            directional_probability=
            directional_probability,

            probability_sample=
            probability_sample,

            current_price=
            current_price,

            signal_atr=
            signal_atr,

            paper_entries_enabled=
            paper_entries_enabled

        )
    )


    print(
        "\n✅ HEAVY HOURLY PIPELINE COMPLETE"
    )


    return {

        "processed_candle_time":
        signal_candle_open_time,


        "dataframe":
        df,


        "result":
        result,


        "integrity":
        integrity,


        "paper_entry":
        paper_entry_result

    }


def _get_latest_time_safely(
        symbol
):

    try:

        latest = (
            get_latest_closed_candle(
                symbol,
                interval="1h"
            )
        )


        if latest is None:

            return None


        return int(
            latest[
                "time"
            ]
        )


    except Exception:

        return None


def start_live_monitor(
        df=None,
        symbol="BTCUSDT",
        price_poll_interval=10,
        candle_poll_interval=60,
        historical_candles=3000,
        initial_train_window=1500,
        test_window=200,
        step=200,
        min_oos_trades=20,
        recent_gap_window_candles=24,
        heavy_retry_seconds=300,
        paper_entries_enabled=False
):

    print(
        "=============================="
    )

    print(
        "📡 ITEM 8 LIVE MONITOR STARTED"
    )

    print(
        "=============================="
    )


    print(
        "✅ Persistent LONG + SHORT paper state"
    )


    print(
        "✅ Fees + SL slippage"
    )


    print(
        "✅ 120s recovery threshold"
    )


    print(
        "✅ 72h recovery hard cap"
    )


    print(
        "✅ Item 7 Light/Heavy architecture"
    )


    print(
        "Paper Entries Enabled:",
        paper_entries_enabled
    )


    if not paper_entries_enabled:

        print(
            "🛑 SAFE SMOKE MODE — NEW ENTRIES OFF"
        )


    if df is not None:

        print(
            "ℹ️ Legacy startup dataframe ignored."
        )


    state = (
        CandleProcessingState()
    )


    startup_price = None


    try:

        startup_price = float(
            get_price(
                symbol
            )
        )


        _manage_open_position(
            symbol,
            startup_price
        )


    except Exception as error:

        print(
            "Startup Position Error:",
            error
        )


    try:

        startup = (
            _run_heavy_cycle(

                symbol=
                symbol,

                historical_candles=
                historical_candles,

                initial_train_window=
                initial_train_window,

                test_window=
                test_window,

                step=
                step,

                min_oos_trades=
                min_oos_trades,

                recent_gap_window_candles=
                recent_gap_window_candles,

                current_price=
                startup_price,

                paper_entries_enabled=
                paper_entries_enabled

            )
        )


        state.mark_success(
            startup[
                "processed_candle_time"
            ]
        )


    except InsufficientContinuousHistoryError as error:

        print(
            "\n⚠️ STARTUP HISTORY BLOCKED:"
        )

        print(
            error
        )


        latest_time = (
            _get_latest_time_safely(
                symbol
            )
        )


        if latest_time is not None:

            state.mark_historical_block(
                latest_time
            )


    except RecentCandleGapError as error:

        print(
            "\n⚠️ STARTUP RECENT GAP:"
        )

        print(
            error
        )


        latest_time = (
            _get_latest_time_safely(
                symbol
            )
        )


        if latest_time is not None:

            state.mark_transient_failure(

                latest_time,

                retry_seconds=
                heavy_retry_seconds

            )


    except Exception as error:

        print(
            "\n❌ STARTUP HEAVY PIPELINE ERROR:",
            error
        )


        latest_time = (
            _get_latest_time_safely(
                symbol
            )
        )


        if latest_time is not None:

            state.mark_transient_failure(

                latest_time,

                retry_seconds=
                heavy_retry_seconds

            )


    next_candle_poll = (
        time.monotonic()
        +
        float(
            candle_poll_interval
        )
    )


    while True:

        current_price = None


        try:

            current_price = float(
                get_price(
                    symbol
                )
            )


            # Paper heartbeat runs BEFORE
            # potential heavy computation.

            _manage_open_position(
                symbol,
                current_price
            )


        except Exception as error:

            print(
                "\n⚠️ Live Position Error:",
                error
            )


        now_monotonic = (
            time.monotonic()
        )


        if (
            now_monotonic
            >=
            next_candle_poll
        ):

            next_candle_poll = (
                now_monotonic
                +
                float(
                    candle_poll_interval
                )
            )


            try:

                latest = (
                    get_latest_closed_candle(

                        symbol,

                        interval="1h"

                    )
                )


                if latest is None:

                    print(
                        "\n⚠️ Light Poll: no closed candle"
                    )


                else:

                    latest_time = int(
                        latest[
                            "time"
                        ]
                    )


                    if state.should_process(

                        latest_time,

                        now_monotonic=
                        now_monotonic

                    ):

                        print(
                            "\n🆕 NEW CLOSED 1H CANDLE DETECTED"
                        )


                        try:

                            heavy = (
                                _run_heavy_cycle(

                                    symbol=
                                    symbol,

                                    historical_candles=
                                    historical_candles,

                                    initial_train_window=
                                    initial_train_window,

                                    test_window=
                                    test_window,

                                    step=
                                    step,

                                    min_oos_trades=
                                    min_oos_trades,

                                    recent_gap_window_candles=
                                    recent_gap_window_candles,

                                    current_price=
                                    current_price,

                                    paper_entries_enabled=
                                    paper_entries_enabled

                                )
                            )


                            processed_time = int(
                                heavy[
                                    "processed_candle_time"
                                ]
                            )


                            if (
                                processed_time
                                <
                                latest_time
                            ):

                                raise Exception(
                                    "Heavy dataset is stale"
                                )


                            state.mark_success(
                                processed_time
                            )


                        except (
                            InsufficientContinuousHistoryError
                        ) as error:

                            print(
                                "\n⚠️ CONTINUOUS HISTORY TOO SHORT:"
                            )

                            print(
                                error
                            )


                            state.mark_historical_block(
                                latest_time
                            )


                        except RecentCandleGapError as error:

                            print(
                                "\n⚠️ RECENT GAP — FAIL CLOSED:"
                            )

                            print(
                                error
                            )


                            state.mark_transient_failure(

                                latest_time,

                                retry_seconds=
                                heavy_retry_seconds,

                                now_monotonic=
                                now_monotonic

                            )


                        except Exception as error:

                            print(
                                "\n❌ HEAVY PIPELINE ERROR:",
                                error
                            )


                            state.mark_transient_failure(

                                latest_time,

                                retry_seconds=
                                heavy_retry_seconds,

                                now_monotonic=
                                now_monotonic

                            )


                    else:

                        print(
                            "\n💡 Light Poll: no heavy work needed"
                        )


                        print(
                            "Latest Closed Candle:",
                            latest_time
                        )


                        print(
                            "Last Processed:",
                            state.last_processed_time
                        )


            except Exception as error:

                print(
                    "\n⚠️ Light Poll Error:",
                    error
                )


        if current_price is not None:

            try:

                print_performance(
                    current_price
                )

            except Exception as error:

                print(
                    "Performance Error:",
                    error
                )


        time.sleep(
            float(
                price_poll_interval
            )
        )