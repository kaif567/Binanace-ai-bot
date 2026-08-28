def generate_final_report(
    optimizer_result,
    validation_result,
    monte_result,
    risk_result,
    strategy_quality=None,
    signal_strength=None,
    direction="FLAT",
    directional_probability=None,
    directional_probability_sample=0,
    paper_status="BLOCKED",
    paper_eligible=False
):

    profit = float(
        optimizer_result.get(
            "profit",
            0
        )
    )

    win_rate = float(
        optimizer_result.get(
            "win_rate",
            0
        )
    )

    profit_factor = float(
        optimizer_result.get(
            "profit_factor",
            0
        )
    )

    trades = int(
        optimizer_result.get(
            "trades",
            0
        )
    )

    if strategy_quality is None:

        strategy_quality = float(
            optimizer_result.get(
                "walk_forward_score",
                0
            )
        )

    monte_probability = (
        monte_result.get(
            "profit_probability",
            0
        )
    )

    risk_level = (
        risk_result.get(
            "risk_level",
            "HIGH"
        )
    )

    return {
        "strategy_quality":
        round(
            float(
                strategy_quality
            ),
            2
        ),

        "signal_strength":
        (
            None
            if signal_strength
            is None
            else
            round(
                float(
                    signal_strength
                ),
                2
            )
        ),

        "direction":
        direction,

        "directional_probability":
        directional_probability,

        "directional_probability_sample":
        int(
            directional_probability_sample
        ),

        "paper_status":
        paper_status,

        "paper_eligible":
        bool(
            paper_eligible
        ),

        "profit_probability":
        monte_probability,

        "risk_level":
        risk_level,

        "oos_sample_quality":
        optimizer_result.get(
            "sample_quality",
            validation_result.get(
                "sample_quality",
                "LOW_SAMPLE_SIZE"
            )
        ),

        "summary": {
            "oos_profit":
            profit,

            "oos_trades":
            trades,

            "oos_win_rate":
            win_rate,

            "oos_profit_factor":
            profit_factor
        }
    }