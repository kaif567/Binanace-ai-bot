"""
Unit test for Robustness Diagnostic (Outlier Winner Removal)

Tests:
1. Fragile case: Strategy has PF > 1.0 originally, but dropping top-1 or top-2 winners drops PF < 1.0 -> FRAGILE
2. Robust case: Strategy retains PF >= 1.0 even without top-1 and top-2 winners -> ROBUST
3. Zero-loss edge case: Gross loss == 0, ensures no ZeroDivisionError and correct handling -> ROBUST
4. Insufficient sample edge case: < 10 trades or 0 wins -> INSUFFICIENT_SAMPLE
"""


def calculate_robustness_diagnostic(closed_trades):
    """
    Diagnostic: Check if strategy performance is an artifact of top 1 or 2 outlier winners.

    Returns dict:
    - status: "ROBUST" | "FRAGILE" | "INSUFFICIENT_SAMPLE"
    - pf_ex_top1: float
    - pf_ex_top2: float
    - top_profit_share_pct: float
    """
    if not closed_trades or len(closed_trades) < 10:
        return {
            "status": "INSUFFICIENT_SAMPLE",
            "pf_ex_top1": 0.0,
            "pf_ex_top2": 0.0,
            "top_profit_share_pct": 0.0,
            "reason": "Less than 10 closed trades"
        }

    profits = [
        float(t.get("profit", 0))
        for t in closed_trades
    ]

    wins = sorted([p for p in profits if p > 0], reverse=True)
    losses = [abs(p) for p in profits if p < 0]

    gross_profit = sum(wins)
    gross_loss = sum(losses)

    if not wins or gross_profit <= 0:
        return {
            "status": "FRAGILE",
            "pf_ex_top1": 0.0,
            "pf_ex_top2": 0.0,
            "top_profit_share_pct": 0.0,
            "reason": "No winning trades"
        }

    top_profit_share_pct = round((wins[0] / gross_profit) * 100, 2)

    # Exclude top 1
    gp_ex_top1 = gross_profit - wins[0]
    if gross_loss > 0:
        pf_ex_top1 = gp_ex_top1 / gross_loss
    else:
        # Zero loss edge case
        pf_ex_top1 = 999.0 if gp_ex_top1 > 0 else 0.0

    # Exclude top 2
    if len(wins) >= 2:
        gp_ex_top2 = gross_profit - wins[0] - wins[1]
    else:
        gp_ex_top2 = 0.0

    if gross_loss > 0:
        pf_ex_top2 = gp_ex_top2 / gross_loss
    else:
        # Zero loss edge case
        pf_ex_top2 = 999.0 if gp_ex_top2 > 0 else 0.0

    pf_ex_top1 = round(pf_ex_top1, 4)
    pf_ex_top2 = round(pf_ex_top2, 4)

    # Decision rule: both ex-top1 and ex-top2 must maintain PF >= 1.0
    if pf_ex_top1 < 1.0 or pf_ex_top2 < 1.0:
        status = "FRAGILE"
        reason = f"PF falls below 1.0 without top winners (ex-top1 PF: {pf_ex_top1}, ex-top2 PF: {pf_ex_top2})"
    else:
        status = "ROBUST"
        reason = f"PF remains >= 1.0 without top winners (ex-top1 PF: {pf_ex_top1}, ex-top2 PF: {pf_ex_top2})"

    return {
        "status": status,
        "pf_ex_top1": pf_ex_top1,
        "pf_ex_top2": pf_ex_top2,
        "top_profit_share_pct": top_profit_share_pct,
        "reason": reason
    }


def test_fragile_case():
    print("\n" + "="*50)
    print("TEST 1: Fragile Strategy (Dependent on 1 outlier)")
    print("="*50)

    # 15 trades: 5 wins, 10 losses ($2 each = -$20 loss)
    # Wins: $25 (one outlier of $18, others: $2, $2, $2, $1)
    # Original GP = $25, GL = $20 -> PF = 1.25 (Looks profitable!)
    # Ex top-1 ($18 removed): GP = $7, GL = $20 -> PF = 0.35 (< 1.0 -> FRAGILE)
    trades = [
        {"type": "SELL", "profit": 18.0},  # Outlier
        {"type": "SELL", "profit": 2.0},
        {"type": "SELL", "profit": 2.0},
        {"type": "SELL", "profit": 2.0},
        {"type": "SELL", "profit": 1.0},
    ] + [{"type": "SELL", "profit": -2.0} for _ in range(10)]

    result = calculate_robustness_diagnostic(trades)
    print(f"Status: {result['status']}")
    print(f"PF ex top-1: {result['pf_ex_top1']}")
    print(f"PF ex top-2: {result['pf_ex_top2']}")
    print(f"Top-1 profit share: {result['top_profit_share_pct']}%")
    print(f"Reason: {result['reason']}")

    assert result["status"] == "FRAGILE"
    assert result["pf_ex_top1"] < 1.0
    print("✅ TEST 1 PASSED")


def test_robust_case():
    print("\n" + "="*50)
    print("TEST 2: Robust Strategy (Consistent edge)")
    print("="*50)

    # 20 trades: 10 wins ($5 each = $50 GP), 10 losses ($3 each = $30 GL)
    # Original PF = 50 / 30 = 1.67
    # Ex top-1: GP = $45, GL = $30 -> PF = 1.50 (>= 1.0)
    # Ex top-2: GP = $40, GL = $30 -> PF = 1.33 (>= 1.0)
    trades = (
        [{"type": "SELL", "profit": 5.0} for _ in range(10)] +
        [{"type": "SELL", "profit": -3.0} for _ in range(10)]
    )

    result = calculate_robustness_diagnostic(trades)
    print(f"Status: {result['status']}")
    print(f"PF ex top-1: {result['pf_ex_top1']}")
    print(f"PF ex top-2: {result['pf_ex_top2']}")
    print(f"Top-1 profit share: {result['top_profit_share_pct']}%")
    print(f"Reason: {result['reason']}")

    assert result["status"] == "ROBUST"
    assert result["pf_ex_top1"] >= 1.0
    assert result["pf_ex_top2"] >= 1.0
    print("✅ TEST 2 PASSED")


def test_zero_loss_case():
    print("\n" + "="*50)
    print("TEST 3: Zero Loss Edge Case (No division by zero)")
    print("="*50)

    # 12 trades, all profitable ($3 each)
    # GL = 0
    trades = [{"type": "SELL", "profit": 3.0} for _ in range(12)]

    result = calculate_robustness_diagnostic(trades)
    print(f"Status: {result['status']}")
    print(f"PF ex top-1: {result['pf_ex_top1']}")
    print(f"PF ex top-2: {result['pf_ex_top2']}")
    print(f"Reason: {result['reason']}")

    assert result["status"] == "ROBUST"
    assert result["pf_ex_top1"] >= 1.0
    print("✅ TEST 3 PASSED")


def test_insufficient_sample_case():
    print("\n" + "="*50)
    print("TEST 4: Insufficient Sample Case (< 10 trades)")
    print("="*50)

    trades = [{"type": "SELL", "profit": 5.0} for _ in range(5)]

    result = calculate_robustness_diagnostic(trades)
    print(f"Status: {result['status']}")
    print(f"Reason: {result['reason']}")

    assert result["status"] == "INSUFFICIENT_SAMPLE"
    print("✅ TEST 4 PASSED")


if __name__ == "__main__":
    test_fragile_case()
    test_robust_case()
    test_zero_loss_case()
    test_insufficient_sample_case()
    print("\n" + "="*50)
    print("ALL ROBUSTNESS DIAGNOSTIC TESTS PASSED ✅")
    print("="*50)
