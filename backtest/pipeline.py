from backtest.monte_carlo import (
    monte_carlo_simulation
)

from backtest.risk import (
    generate_risk_report
)

from backtest.report import (
    generate_final_report
)

from backtest.optimizer import (
    prepare_strategy_dataframe
)

from strategy.scoring import (
    calculate_score
)

from database.memory import (
    save_strategy
)

from database.self_optimizer import (
    improve_strategy
)

from database.confidence import (
    get_directional_probability,
    MIN_DIRECTIONAL_SAMPLES
)

from indicators.regime import classify_regime


STRATEGY_QUALITY_V2_GATE = 60.0

MIN_OOS_TRADES_GATE = 50

MIN_PROFIT_FACTOR_GATE = 1.20

COLLECTION_SIGNAL_GATE = 65.0

CALIBRATED_SIGNAL_GATE = 50.0

DIRECTIONAL_PROBABILITY_GATE = 55.0

# ── Phase 1 Chop Filter — Regime parameters ──────────────────────────────────
# Derived from walk-forward ADX+ATR threshold sweep on 2000 1h BTCUSDT candles.
# ADX>25 → 13 OOS trades, Strategy Quality V2 = 50.20 (+8.0 vs unfiltered 42.2)
# ATR surge >40% in 12h → additional HIGH_VOLATILITY block
#
# IMPORTANT: Do NOT change these values without re-running backtest/threshold_sweep.py
# on updated historical data. Changing thresholds without validation violates
# WORKING_PRINCIPLES Rule 5 (validate against real historical data).
# ─────────────────────────────────────────────────────────────────────────────
REGIME_PARAMS = {
    "adx_trending_thresh": 25.0,
    "adx_ranging_thresh": 18.0,
    "atr_lookback": 12,
    "atr_change_thresh": 0.40,
}


def determine_paper_eligibility(
    strategy_quality,
    signal_strength,
    directional_probability,
    directional_probability_sample,
    direction,
    oos_sample_quality,
    oos_trades,
    oos_profit_factor,
    oos_profit,
    robustness_status="ROBUST",
    regime_status="TRENDING"
):

    strategy_quality = float(
        strategy_quality
    )

    signal_strength = float(
        signal_strength
    )

    directional_probability_sample = int(
        directional_probability_sample
    )

    oos_trades = int(
        oos_trades
    )

    oos_profit_factor = float(
        oos_profit_factor
    )

    oos_profit = float(
        oos_profit
    )

    if direction not in [
        "UP",
        "DOWN"
    ]:

        return {
            "eligible":
            False,

            "mode":
            "NO_DIRECTION",

            "reason":
            "No actionable direction"
        }

    if (
        oos_sample_quality
        !=
        "OOS_SUFFICIENT"
    ):

        return {
            "eligible":
            False,

            "mode":
            "INSUFFICIENT_OOS_SAMPLE",

            "reason":
            "Strategy does not have enough OOS trades"
        }

    # =========================
    # MULTI-CONDITION GATE (V2)
    # =========================

    if (
        strategy_quality
        <
        STRATEGY_QUALITY_V2_GATE
    ):

        return {
            "eligible":
            False,

            "mode":
            "STRATEGY_QUALITY_BLOCKED",

            "reason":
            f"Strategy quality V2 below {STRATEGY_QUALITY_V2_GATE}"
        }

    if (
        oos_trades
        <
        MIN_OOS_TRADES_GATE
    ):

        return {
            "eligible":
            False,

            "mode":
            "OOS_TRADES_BLOCKED",

            "reason":
            f"OOS trades {oos_trades} below {MIN_OOS_TRADES_GATE}"
        }

    if (
        oos_profit_factor
        <
        MIN_PROFIT_FACTOR_GATE
    ):

        return {
            "eligible":
            False,

            "mode":
            "PROFIT_FACTOR_BLOCKED",

            "reason":
            f"Profit factor {oos_profit_factor:.4f} below {MIN_PROFIT_FACTOR_GATE}"
        }

    avg_return_per_trade = (
        oos_profit / oos_trades
        if oos_trades > 0
        else 0
    )

    if avg_return_per_trade <= 0:

        return {
            "eligible":
            False,

            "mode":
            "AVG_RETURN_BLOCKED",

            "reason":
            f"Avg return per trade ${avg_return_per_trade:.4f} not positive"
        }

    if robustness_status == "FRAGILE":

        return {
            "eligible":
            False,

            "mode":
            "ROBUSTNESS_FRAGILE_BLOCKED",

            "reason":
            "Strategy failed outlier removal test (PF < 1.0 without top winners)"
        }

    # =========================
    # GATE #6: REGIME FILTER
    # (Phase 1 Chop Filter)
    # =========================
    # Block trades when current market regime is RANGING or HIGH_VOLATILITY.
    # TRENDING or UNKNOWN are allowed through.
    # UNKNOWN = insufficient indicator data (e.g. first candle) → pass through
    # so data gaps never silently block potentially valid trades.

    if regime_status not in ("TRENDING", "UNKNOWN"):

        return {
            "eligible":
            False,

            "mode":
            "REGIME_BLOCKED",

            "reason":
            f"Market regime is {regime_status} — entry blocked (chop filter)"
        }


    # =========================
    # COLLECTION MODE
    # =========================

    if (
        directional_probability_sample
        <
        MIN_DIRECTIONAL_SAMPLES
    ):

        if (
            signal_strength
            <
            COLLECTION_SIGNAL_GATE
        ):

            return {
                "eligible":
                False,

                "mode":
                "COLLECTION_SIGNAL_BLOCKED",

                "reason":
                "Signal strength below 65 during collection mode"
            }

        return {
            "eligible":
            True,

            "mode":
            "PAPER_COLLECTION_MODE",

            "reason":
            "Collecting direction-specific probability data"
        }

    # =========================
    # CALIBRATED MODE
    # =========================

    if (
        signal_strength
        <
        CALIBRATED_SIGNAL_GATE
    ):

        return {
            "eligible":
            False,

            "mode":
            "CALIBRATED_SIGNAL_BLOCKED",

            "reason":
            "Signal strength below 50"
        }

    if directional_probability is None:

        return {
            "eligible":
            False,

            "mode":
            "PROBABILITY_UNAVAILABLE",

            "reason":
            "Directional probability unavailable"
        }

    if (
        float(
            directional_probability
        )
        <
        DIRECTIONAL_PROBABILITY_GATE
    ):

        return {
            "eligible":
            False,

            "mode":
            "PROBABILITY_BLOCKED",

            "reason":
            "Directional probability below 55%"
        }

    return {
        "eligible":
        True,

        "mode":
        "PAPER_CALIBRATED_MODE",

        "reason":
        "Separated metric gates passed"
    }


def run_ai_pipeline(
    df,
    symbol="BTCUSDT",
    initial_train_window=300,
    test_window=50,
    step=50,
    min_oos_trades=20
):

    print(
        "=============================="
    )

    print(
        "🤖 AI STRATEGY PIPELINE"
    )

    print(
        "=============================="
    )

    print(
        "\n🔎 REAL WALK-FORWARD OPTIMIZATION..."
    )

    optimized = improve_strategy(
        df,

        initial_train_window=
        initial_train_window,

        test_window=
        test_window,

        step=
        step,

        min_oos_trades=
        min_oos_trades,

        initial_balance=1000,

        trade_amount=100,

        fee=0.001
    )

    if (
        optimized.get(
            "status"
        )
        !=
        "completed"
    ):

        raise Exception(
            optimized.get(
                "message",
                "Walk-forward optimizer failed"
            )
        )

    validation = optimized[
        "walk_forward"
    ]

    oos = optimized[
        "oos"
    ]

    strategy_params = dict(
        optimized[
            "strategy"
        ]
    )

    strategy_quality = round(
        float(
            optimized.get(
                "walk_forward_score",
                0
            )
        ),
        2
    )

    best = {
        "strategy":
        strategy_params,

        "ema_fast":
        strategy_params.get(
            "ema_fast"
        ),

        "ema_slow":
        strategy_params.get(
            "ema_slow"
        ),

        "sl":
        strategy_params.get(
            "sl"
        ),

        "tp":
        strategy_params.get(
            "tp"
        ),

        "profit":
        oos.get(
            "profit",
            0
        ),

        "trades":
        oos.get(
            "trades",
            0
        ),

        "wins":
        oos.get(
            "wins",
            0
        ),

        "losses":
        oos.get(
            "losses",
            0
        ),

        "win_rate":
        oos.get(
            "win_rate",
            0
        ),

        "profit_factor":
        oos.get(
            "profit_factor",
            0
        ),

        "history":
        oos.get(
            "history",
            []
        ),

        "sample_quality":
        oos.get(
            "sample_quality",
            "LOW_SAMPLE_SIZE"
        ),

        "strategy_quality":
        strategy_quality,

        "walk_forward_score":
        strategy_quality
    }

    # =========================
    # CURRENT SIGNAL
    # =========================

    signal_df = (
        prepare_strategy_dataframe(
            df,
            strategy_params
        )
    )

    market_analysis = (
        calculate_score(
            signal_df,
            best
        )
    )

    market_signal = (
        market_analysis.get(
            "signal",
            "HOLD"
        )
    )

    direction = (
        market_analysis.get(
            "direction",
            "FLAT"
        )
    )

    market_score = float(
        market_analysis.get(
            "market_score",
            market_analysis.get(
                "score",
                50
            )
        )
    )

    signal_strength = float(
        market_analysis.get(
            "signal_strength",
            market_analysis.get(
                "strength",
                0
            )
        )
    )

    reasons = (
        market_analysis.get(
            "reasons",
            []
        )
    )

    # =========================
    # HISTORICAL PROBABILITY
    # =========================

    probability_stats = (
        get_directional_probability(
            direction
        )
    )

    directional_probability = (
        probability_stats.get(
            "directional_probability"
        )
    )

    directional_probability_sample = int(
        probability_stats.get(
            "sample",
            0
        )
    )

    # =========================
    # REGIME STATUS (Gate #6)
    # =========================
    # Classify current market regime from the live 1h candle DataFrame.
    # classify_regime reads df.iloc[-1] for ADX/ATR — always the last
    # closed candle. This is identical to what the backtest engine does
    # during signal generation (df.iloc[:i+1]), ensuring live ↔ backtest
    # consistency (no mismatch like the earlier SL-slippage case).

    regime_status = classify_regime(df, **REGIME_PARAMS)


    paper_gate = (
        determine_paper_eligibility(
            strategy_quality=
            strategy_quality,

            signal_strength=
            signal_strength,

            directional_probability=
            directional_probability,

            directional_probability_sample=
            directional_probability_sample,

            direction=
            direction,

            oos_sample_quality=
            oos.get(
                "sample_quality",
                "LOW_SAMPLE_SIZE"
            ),

            oos_trades=
            oos.get(
                "trades",
                0
            ),

            oos_profit_factor=
            oos.get(
                "profit_factor",
                0
            ),

            oos_profit=
            oos.get(
                "profit",
                0
            ),

            robustness_status=
            oos.get(
                "robustness_status",
                "INSUFFICIENT_SAMPLE"
            ),

            regime_status=regime_status
        )
    )

    paper_eligible = (
        paper_gate[
            "eligible"
        ]
    )

    paper_mode = (
        paper_gate[
            "mode"
        ]
    )

    paper_reason = (
        paper_gate[
            "reason"
        ]
    )

    # =========================
    # MONTE CARLO + RISK
    # =========================

    monte = (
        monte_carlo_simulation(
            best.get(
                "history",
                []
            )
        )
    )

    risk = (
        generate_risk_report(
            best,
            monte
        )
    )

    report = (
        generate_final_report(
            best,
            validation,
            monte,
            risk,

            strategy_quality=
            strategy_quality,

            signal_strength=
            signal_strength,

            direction=
            direction,

            directional_probability=
            directional_probability,

            directional_probability_sample=
            directional_probability_sample,

            paper_status=
            paper_mode,

            paper_eligible=
            paper_eligible
        )
    )

    best[
        "paper_status"
    ] = paper_mode

    best[
        "paper_eligible"
    ] = paper_eligible

    best[
        "regime_status"
    ] = regime_status

    print(
        "\n=============================="
    )

    print(
        "SEPARATED METRICS"
    )

    print(
        "=============================="
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
        directional_probability_sample
    )

    print(
        "Probability Status:",
        probability_stats.get(
            "status"
        )
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
        "Paper Reason:",
        paper_reason
    )

    print(
        "Regime Status:",
        regime_status
    )

    print(
        "\n💾 Saving Strategy Memory..."
    )

    save_strategy(
        symbol,
        best,
        report
    )

    return {
        "best_strategy":
        best,

        "all_strategies":
        validation.get(
            "latest_training_ranked",
            []
        ),

        "validation":
        validation,

        "monte_carlo":
        monte,

        "risk":
        risk,

        "report":
        report,

        "final_report":
        report,

        "strategy_quality":
        strategy_quality,

        "market_signal":
        market_signal,

        "direction":
        direction,

        "market_score":
        market_score,

        "signal_strength":
        signal_strength,

        "directional_probability":
        directional_probability,

        "directional_probability_sample":
        directional_probability_sample,

        "probability_status":
        probability_stats.get(
            "status"
        ),

        "conditional_accuracy":
        probability_stats.get(
            "conditional_accuracy"
        ),

        "paper_eligible":
        paper_eligible,

        "paper_mode":
        paper_mode,

        "paper_reason":
        paper_reason,

        "status":
        paper_mode,

        "reasons":
        reasons,

        "regime_status":
        regime_status,

        "paper_trade":
        None
    }