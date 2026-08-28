from data.binance_api import (
    get_closed_candles
)

from indicators.technical import (
    add_indicators
)

from backtest.validation import (
    walk_forward_test
)


symbol = "BTCUSDT"


print(
    "Running Real Walk Forward Test..."
)


df = get_closed_candles(
    symbol,
    interval="1h",
    limit=500
)

df = add_indicators(
    df
)


result = walk_forward_test(
    df,

    initial_train_window=300,

    test_window=50,

    step=50,

    min_oos_trades=20
)


print(
    "\n===================="
)

print(
    "WALK-FORWARD REPORT"
)

print(
    "===================="
)


if result.get(
    "status"
) != "completed":

    print(
        result
    )

else:
    print(
        f"""
Mode:
{result['mode']}

Boundary Rule:
{result['boundary_rule']}

Folds:
{result['fold_count']}

OOS Profit:
${result['profit']}

OOS Trades:
{result['trades']}

OOS Wins:
{result['wins']}

OOS Losses:
{result['losses']}

OOS Win Rate:
{result['win_rate']}%

OOS Profit Factor:
{result['profit_factor']}

Walk-Forward Score:
{result['walk_forward_score']}

Sample Quality:
{result['sample_quality']}

Latest Strategy:
{result['latest_strategy']}
"""
    )

    print(
        "\nFOLD DETAILS"
    )

    for fold in result[
        "folds"
    ]:
        print(
            f"""
Fold {fold['fold']}

Train:
{fold['train_start']} -> {fold['train_end']}

Test:
{fold['test_start']} -> {fold['test_end']}

Strategy:
{fold['selected_strategy']}

Test Profit:
{fold['testing']['profit']}

Test Trades:
{fold['testing']['trades']}

Test Win Rate:
{fold['testing']['win_rate']}%

--------------------
"""
        )