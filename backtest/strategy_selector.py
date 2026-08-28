def select_best_strategy(
    strategies
):
    """
    Rank strategies WITHOUT calculating a
    second score from the same evidence.

    Priority:
    1. walk_forward_score
    2. ai_score
    3. training_score
    4. score
    """

    if isinstance(
        strategies,
        dict
    ):
        strategies = [
            strategies
        ]

    ranked = []

    for strategy in strategies:
        if not isinstance(
            strategy,
            dict
        ):
            continue

        ranking_score = float(
            strategy.get(
                "walk_forward_score",

                strategy.get(
                    "ai_score",

                    strategy.get(
                        "training_score",

                        strategy.get(
                            "score",
                            0
                        )
                    )
                )
            )
        )

        copied = dict(
            strategy
        )

        copied[
            "ranking_score"
        ] = ranking_score

        ranked.append(
            copied
        )

    if not ranked:
        raise Exception(
            "No valid strategies"
        )

    ranked.sort(
        key=lambda item:
        item.get(
            "ranking_score",
            0
        ),
        reverse=True
    )

    print(
        "\n===== RANKED STRATEGIES ====="
    )

    for item in ranked[:3]:
        print(
            "Score:",
            item.get(
                "ranking_score"
            ),
            "| Strategy:",
            item.get(
                "strategy",
                {}
            )
        )

    return ranked