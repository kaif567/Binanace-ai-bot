"""
Unit Test: Training Score V2 Formula (Known Cases from 2024-03 Window)

Validates V2 training score implementation against verified calculations.
"""

import math
from backtest.optimizer import calculate_training_score


def test_known_case_1():
    """2024-03 burn-in 200: 20/50 (0.01/0.08) — 14 trades"""
    result = {
        "trades": 14,
        "profit": 11.90,
        "profit_factor": 1.99,
        "win_rate": 28.6
    }

    expected = 66.80
    actual = calculate_training_score(result)

    assert abs(actual - expected) < 0.1, f"Expected {expected}, got {actual}"
    print(f"✓ Case 1: 14 trades, $11.90, PF 1.99 → {actual} (expected {expected})")


def test_known_case_2():
    """2024-03 burn-in 200: 20/50 (0.02/0.05) — 11 trades"""
    result = {
        "trades": 11,
        "profit": 13.50,
        "profit_factor": 2.23,
        "win_rate": 54.5
    }

    expected = 65.48
    actual = calculate_training_score(result)

    assert abs(actual - expected) < 0.1, f"Expected {expected}, got {actual}"
    print(f"✓ Case 2: 11 trades, $13.50, PF 2.23 → {actual} (expected {expected})")


def test_edge_case_zero_trades():
    """Edge: 0 trades"""
    result = {
        "trades": 0,
        "profit": 0,
        "profit_factor": 0,
        "win_rate": 0
    }

    expected = 0.0
    actual = calculate_training_score(result)

    assert actual == expected, f"Expected {expected}, got {actual}"
    print(f"✓ Edge: 0 trades → {actual}")


def test_edge_case_single_trade_loss():
    """Edge: 1 trade, loss"""
    result = {
        "trades": 1,
        "profit": -1.20,
        "profit_factor": 0.0,
        "win_rate": 0.0
    }

    actual = calculate_training_score(result)

    # 1 trade = 4.76% confidence, heavy shrinkage toward 50
    assert 45.0 < actual < 50.0, f"Expected 45-50 range, got {actual}"
    print(f"✓ Edge: 1 trade loss → {actual} (heavy shrinkage)")


def test_edge_case_single_trade_win():
    """Edge: 1 trade, win"""
    result = {
        "trades": 1,
        "profit": 5.0,
        "profit_factor": 5.0,
        "win_rate": 100.0
    }

    actual = calculate_training_score(result)

    # 1 trade = 4.76% confidence, should shrink heavily toward 50 even for big win
    assert 50.0 < actual < 55.0, f"Expected 50-55 range, got {actual}"
    print(f"✓ Edge: 1 trade win → {actual} (heavy shrinkage)")


def test_sample_size_shrinkage():
    """Shrinkage verification: n/(n+20) at different N"""
    cases = [
        (2, 2/(2+20)),    # 9.1%
        (5, 5/(5+20)),    # 20%
        (10, 10/(10+20)), # 33.3%
        (20, 20/(20+20)), # 50%
        (50, 50/(50+20)), # 71.4%
    ]

    for n, expected_confidence in cases:
        result = {
            "trades": n,
            "profit": n * 1.0,  # $1 profit per trade
            "profit_factor": 1.5,
            "win_rate": 50.0
        }

        actual = calculate_training_score(result)

        # Manual calculation
        avg_return = 1.0 / 100.0  # 1% per trade
        return_signal = math.tanh(avg_return / 0.005)
        pf_signal = math.tanh(math.log(1.5) / math.log(2.5))
        edge = 0.60 * return_signal + 0.40 * pf_signal
        raw_score = 50.0 + 50.0 * edge
        expected_score = 50.0 + expected_confidence * (raw_score - 50.0)

        assert abs(actual - expected_score) < 0.1, f"N={n}: Expected {expected_score:.2f}, got {actual}"
        print(f"✓ Shrinkage N={n}: confidence {expected_confidence*100:.1f}% → score {actual}")


def test_negative_profit_factor():
    """Edge: All losses (PF = 0)"""
    result = {
        "trades": 10,
        "profit": -10.0,
        "profit_factor": 0.0,
        "win_rate": 0.0
    }

    actual = calculate_training_score(result)

    # PF=0 → pf_signal = -1.0 (max negative)
    # avg_return = -1.0% → return_signal negative
    # Confidence = 10/(10+20) = 33%
    # Should be well below 50
    assert actual < 45.0, f"Expected <45, got {actual}"
    print(f"✓ Edge: All losses (PF=0) → {actual}")


if __name__ == "__main__":
    print("="*70)
    print("TRAINING SCORE V2 UNIT TESTS")
    print("="*70)
    print()

    test_known_case_1()
    test_known_case_2()
    test_edge_case_zero_trades()
    test_edge_case_single_trade_loss()
    test_edge_case_single_trade_win()
    test_sample_size_shrinkage()
    test_negative_profit_factor()

    print()
    print("="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
