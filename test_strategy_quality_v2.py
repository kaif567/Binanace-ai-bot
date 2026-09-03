"""
Unit test for Strategy Quality V2 formula.

Tests the new calculate_oos_strategy_quality() function
against verified historical backtest results.

V2 Formula:
- return_signal = tanh(avg_return / 0.005)
- pf_signal = tanh(ln(PF) / ln(2.5))
- edge = 0.60 × return_signal + 0.40 × pf_signal
- raw_score = 50 + 50 × edge
- confidence = n / (n + 50)
- final_score = 50 + confidence × (raw_score - 50)
"""

import math


def calculate_oos_strategy_quality(result):
    """
    V2 Strategy Quality formula for OOS results only.

    Component 1 (60%): Normalized return signal via tanh
    Component 2 (40%): Profit factor signal via tanh
    Sample-size shrinkage: n/(n+50)

    Returns score 0-100 where:
        50 = neutral/no-edge
        <50 = negative evidence
        >50 = positive evidence
    """
    closed_trades = int(result.get("trades", 0))

    if closed_trades == 0:
        return 0.0

    profit = float(result.get("profit", 0))
    trade_amount = 100  # Standard from backtest
    profit_factor = float(result.get("profit_factor", 0))

    # Component 1: Normalized return signal
    avg_return = (profit / closed_trades) / trade_amount
    return_signal = math.tanh(avg_return / 0.005)

    # Component 2: PF signal
    if profit_factor > 0:
        pf_signal = math.tanh(math.log(profit_factor) / math.log(2.5))
    else:
        pf_signal = -1.0

    # Weighted edge
    edge = 0.60 * return_signal + 0.40 * pf_signal

    # Raw score (before shrinkage)
    raw_score = 50 + 50 * edge

    # Sample-size shrinkage
    confidence = closed_trades / (closed_trades + 50)
    final_score = 50 + confidence * (raw_score - 50)

    return round(final_score, 2)


def test_case_1_negative_edge():
    """
    Historical Run "34.29" (old score)
    Negative edge case — loses money
    """
    print("\n" + "="*60)
    print("TEST CASE 1: Negative Edge (Historical '34.29' run)")
    print("="*60)

    result = {
        "trades": 29,
        "profit": -8.1702,
        "profit_factor": 0.7919,
        "win_rate": 31.03,
        "wins": 9,
        "losses": 20
    }

    print(f"\nInput Metrics:")
    print(f"  Trades: {result['trades']}")
    print(f"  Net Profit: ${result['profit']:.4f}")
    print(f"  Avg $/trade: ${result['profit'] / result['trades']:.4f}")
    print(f"  Profit Factor: {result['profit_factor']:.4f}")
    print(f"  Win Rate: {result['win_rate']:.2f}%")

    score = calculate_oos_strategy_quality(result)

    print(f"\nV2 Strategy Quality: {score}")
    print(f"Expected: 42.54 ± 0.5")

    # Verify
    expected = 42.54
    tolerance = 0.5

    assert abs(score - expected) <= tolerance, \
        f"Score {score} outside expected range [{expected - tolerance}, {expected + tolerance}]"

    print("✅ PASS")
    return score


def test_case_2_positive_edge_low_sample():
    """
    Historical Run "83.91" (old score, outlier-audit)
    Positive edge but low sample size
    """
    print("\n" + "="*60)
    print("TEST CASE 2: Positive Edge, Low Sample (Historical '83.91' run)")
    print("="*60)

    result = {
        "trades": 23,
        "profit": 8.9203,
        "profit_factor": 1.3431,
        "win_rate": 34.78,
        "wins": 8,
        "losses": 15
    }

    print(f"\nInput Metrics:")
    print(f"  Trades: {result['trades']}")
    print(f"  Net Profit: ${result['profit']:.4f}")
    print(f"  Avg $/trade: ${result['profit'] / result['trades']:.4f}")
    print(f"  Profit Factor: {result['profit_factor']:.4f}")
    print(f"  Win Rate: {result['win_rate']:.2f}%")

    score = calculate_oos_strategy_quality(result)

    print(f"\nV2 Strategy Quality: {score}")
    print(f"Expected: 58.12 ± 0.5")

    # Verify
    expected = 58.12
    tolerance = 0.5

    assert abs(score - expected) <= tolerance, \
        f"Score {score} outside expected range [{expected - tolerance}, {expected + tolerance}]"

    print("✅ PASS")
    return score


def test_case_3_near_neutral():
    """
    Historical Run "41.09" (old score, burn-in-100)
    Near-zero edge — barely profitable
    """
    print("\n" + "="*60)
    print("TEST CASE 3: Near-Neutral Edge (Historical '41.09' run)")
    print("="*60)

    result = {
        "trades": 27,
        "profit": 0.5076,  # 27 * 0.0188 ≈ 0.5076
        "profit_factor": 1.0145,
        "win_rate": 33.33,
        "wins": 9,
        "losses": 18
    }

    print(f"\nInput Metrics:")
    print(f"  Trades: {result['trades']}")
    print(f"  Net Profit: ${result['profit']:.4f}")
    print(f"  Avg $/trade: ${result['profit'] / result['trades']:.4f}")
    print(f"  Profit Factor: {result['profit_factor']:.4f}")
    print(f"  Win Rate: {result['win_rate']:.2f}%")

    score = calculate_oos_strategy_quality(result)

    print(f"\nV2 Strategy Quality: {score}")
    print(f"Expected: 50.51 ± 0.5")

    # Verify
    expected = 50.51
    tolerance = 0.5

    assert abs(score - expected) <= tolerance, \
        f"Score {score} outside expected range [{expected - tolerance}, {expected + tolerance}]"

    print("✅ PASS")
    return score


def test_zero_trades_edge_case():
    """
    Edge case: zero trades should return 0.0
    """
    print("\n" + "="*60)
    print("TEST CASE 4: Zero Trades Edge Case")
    print("="*60)

    result = {
        "trades": 0,
        "profit": 0,
        "profit_factor": 0
    }

    score = calculate_oos_strategy_quality(result)

    print(f"\nV2 Strategy Quality: {score}")
    print(f"Expected: 0.0")

    assert score == 0.0, f"Zero trades should return 0.0, got {score}"

    print("✅ PASS")
    return score


if __name__ == "__main__":
    print("\n" + "="*60)
    print("STRATEGY QUALITY V2 FORMULA UNIT TEST")
    print("="*60)
    print("\nTesting against verified historical backtest results")

    try:
        score1 = test_case_1_negative_edge()
        score2 = test_case_2_positive_edge_low_sample()
        score3 = test_case_3_near_neutral()
        score4 = test_zero_trades_edge_case()

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✅")
        print("="*60)

        print("\nSummary:")
        print(f"  Case 1 (negative edge):      {score1:.2f}")
        print(f"  Case 2 (positive, low n):    {score2:.2f}")
        print(f"  Case 3 (near-neutral):       {score3:.2f}")
        print(f"  Case 4 (zero trades):        {score4:.2f}")

        print("\nV2 formula is working correctly!")
        print("Ready for production integration.")

    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60)
        print(f"\nError: {e}")
        raise
