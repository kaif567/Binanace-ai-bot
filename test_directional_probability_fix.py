"""
Unit Test: Directional Probability Calibration Status (Finding #6 Fix)

Validates that MIN_DIRECTIONAL_SAMPLES threshold counts only decisive outcomes
(CORRECT + WRONG) to trigger CALIBRATED status, excluding NEUTRAL outcomes.
"""

from database.confidence import get_directional_probability


def make_mock_decision(direction, result):
    return {
        "version": 3,
        "timing_model": "CLOSED_CANDLE_NEXT_CLOSED_CANDLE",
        "label_model": "FEES_PLUS_ATR_THRESHOLD_V1",
        "direction": direction,
        "status": "EVALUATED",
        "result": result
    }


def test_neutral_does_not_trigger_calibration():
    """
    Test Case: 6 correct + 0 wrong + 44 neutral = 50 total samples.
    Old bug: 50 total >= 50 threshold -> CALIBRATED (WRONG)
    Fix: 6 decisive < 50 threshold -> INSUFFICIENT_DATA (CORRECT)
    """
    decisions = []
    for _ in range(6):
        decisions.append(make_mock_decision("UP", "CORRECT"))
    for _ in range(0):
        decisions.append(make_mock_decision("UP", "WRONG"))
    for _ in range(44):
        decisions.append(make_mock_decision("UP", "NEUTRAL"))

    res = get_directional_probability("UP", decisions=decisions, minimum_samples=50)

    assert res["status"] == "INSUFFICIENT_DATA", f"Expected INSUFFICIENT_DATA, got {res['status']}"
    assert res["directional_probability"] is None, f"Expected None probability, got {res['directional_probability']}"
    assert res["sample"] == 50
    assert res["directional_outcomes"] == 6
    assert res["correct"] == 6
    assert res["wrong"] == 0
    assert res["neutral"] == 44
    # Smoothed estimate calculation still includes 0.5 * neutral: (6 + 22 + 1) / (50 + 2) = 29/52 = 55.77%
    assert res["smoothed_estimate"] == 55.77
    print("✓ Test 1 Passed: 6 correct + 44 neutral -> INSUFFICIENT_DATA (directional_outcomes = 6 < 50)")


def test_decisive_samples_trigger_calibration():
    """
    Test Case: 30 correct + 20 wrong + 10 neutral = 60 total, 50 decisive.
    Decisive = 50 >= 50 threshold -> CALIBRATED
    """
    decisions = []
    for _ in range(30):
        decisions.append(make_mock_decision("UP", "CORRECT"))
    for _ in range(20):
        decisions.append(make_mock_decision("UP", "WRONG"))
    for _ in range(10):
        decisions.append(make_mock_decision("UP", "NEUTRAL"))

    res = get_directional_probability("UP", decisions=decisions, minimum_samples=50)

    assert res["status"] == "CALIBRATED", f"Expected CALIBRATED, got {res['status']}"
    assert res["directional_probability"] is not None
    assert res["directional_outcomes"] == 50
    assert res["sample"] == 60
    # Smoothed estimate: (30 + 0.5*10 + 1) / (60 + 2) = 36/62 = 58.06%
    assert res["smoothed_estimate"] == 58.06
    assert res["directional_probability"] == 58.06
    print("✓ Test 2 Passed: 30 correct + 20 wrong + 10 neutral -> CALIBRATED (directional_outcomes = 50 >= 50)")


def test_near_threshold_edge_case():
    """
    Test Case: 25 correct + 24 wrong + 100 neutral = 149 total, 49 decisive.
    Decisive = 49 < 50 threshold -> INSUFFICIENT_DATA
    """
    decisions = []
    for _ in range(25):
        decisions.append(make_mock_decision("DOWN", "CORRECT"))
    for _ in range(24):
        decisions.append(make_mock_decision("DOWN", "WRONG"))
    for _ in range(100):
        decisions.append(make_mock_decision("DOWN", "NEUTRAL"))

    res = get_directional_probability("DOWN", decisions=decisions, minimum_samples=50)

    assert res["status"] == "INSUFFICIENT_DATA"
    assert res["directional_probability"] is None
    assert res["directional_outcomes"] == 49
    assert res["sample"] == 149
    print("✓ Test 3 Passed: 49 decisive + 100 neutral -> INSUFFICIENT_DATA (directional_outcomes = 49 < 50)")


if __name__ == "__main__":
    print("=" * 70)
    print("DIRECTIONAL PROBABILITY CALIBRATION UNIT TESTS")
    print("=" * 70)
    print()

    test_neutral_does_not_trigger_calibration()
    test_decisive_samples_trigger_calibration()
    test_near_threshold_edge_case()

    print()
    print("=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
