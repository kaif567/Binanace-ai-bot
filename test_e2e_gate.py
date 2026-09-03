"""
End-to-End Integration Test for Paper-Eligibility Gate

Tests the historical 23-trade "fragile" sample:
- 23 closed trades (8 wins, 15 losses)
- Net Profit: $8.9203
- Profit Factor: 1.3431 (Original)
- Ex-top2 Profit Factor: 0.9739 (< 1.0 -> FRAGILE)
- V2 Strategy Quality Score: 58.11 (< 60.0)

Verifies:
1. Complete rejection across the 5-condition gate
2. Exact failure mode and reason reporting
3. Individual gate diagnostic isolation (what happens if each condition is tested)
"""

from backtest.optimizer import calculate_oos_strategy_quality
from backtest.validation import _calculate_robustness_diagnostic
from backtest.pipeline import determine_paper_eligibility


def test_23_trade_fragile_sample():
    print("\n" + "="*60)
    print("E2E TEST: 23-Trade Fragile Historical Sample")
    print("="*60)

    # Reconstruct 23 closed trades:
    # 8 wins totaling $34.9203
    # 15 losses totaling -$26.0000
    # Net Profit = +$8.9203
    # Original PF = 34.9203 / 26.0 = 1.3431
    # Top 2 wins: $5.0000 + $4.6000 = $9.6000
    # Ex-top2 GP = 34.9203 - 9.6000 = $25.3203
    # Ex-top2 PF = 25.3203 / 26.0 = 0.9739 (< 1.0 -> FRAGILE)
    wins = [5.0000, 4.6000, 4.3203, 4.2000, 4.2000, 4.2000, 4.2000, 4.2000]
    losses = [-1.73333333] * 15  # Sum ≈ -26.0

    trades = (
        [{"type": "SELL", "profit": w} for w in wins] +
        [{"type": "SELL", "profit": l} for l in losses]
    )

    # 1. Compute Robustness Diagnostic
    robustness = _calculate_robustness_diagnostic(trades)
    print("\n--- 1. ROBUSTNESS DIAGNOSTIC ---")
    print(f"Status:             {robustness['status']}")
    print(f"PF ex-top1:         {robustness['pf_ex_top1']}")
    print(f"PF ex-top2:         {robustness['pf_ex_top2']}")
    print(f"Top-1 Profit Share: {robustness['top_profit_share_pct']}%")
    print(f"Reason:             {robustness['reason']}")

    # 2. Compute V2 Strategy Quality
    metrics = {
        "trades": len(trades),
        "profit": sum(wins) + sum(losses),
        "profit_factor": sum(wins) / abs(sum(losses)),
        "win_rate": (len(wins) / len(trades)) * 100
    }
    v2_score = calculate_oos_strategy_quality(metrics)
    print("\n--- 2. V2 STRATEGY QUALITY SCORE ---")
    print(f"V2 Score:           {v2_score} (Expected: 58.11 ±0.5)")

    # 3. Test determine_paper_eligibility() in Normal Production Flow
    print("\n--- 3. FULL PIPELINE GATE EVALUATION (Sequential) ---")
    gate_result = determine_paper_eligibility(
        strategy_quality=v2_score,
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=30,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=metrics["trades"],
        oos_profit_factor=metrics["profit_factor"],
        oos_profit=metrics["profit"],
        robustness_status=robustness["status"]
    )

    print(f"Eligible:           {gate_result['eligible']}")
    print(f"Mode:               {gate_result['mode']}")
    print(f"Reason:             {gate_result['reason']}")

    assert gate_result["eligible"] is False, "Gate should REJECT fragile sample"
    assert gate_result["mode"] == "STRATEGY_QUALITY_BLOCKED", f"Expected STRATEGY_QUALITY_BLOCKED, got {gate_result['mode']}"

    # 4. Diagnostic: What if V2 Score passed (e.g. forced 65.0)?
    print("\n--- 4. GATE ISOLATION 1 (If V2 Score was >= 60.0) ---")
    gate_forced_v2 = determine_paper_eligibility(
        strategy_quality=65.0,  # Simulate V2 pass
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=30,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=metrics["trades"],
        oos_profit_factor=metrics["profit_factor"],
        oos_profit=metrics["profit"],
        robustness_status=robustness["status"]
    )
    print(f"Eligible:           {gate_forced_v2['eligible']}")
    print(f"Mode:               {gate_forced_v2['mode']}")
    print(f"Reason:             {gate_forced_v2['reason']}")

    assert gate_forced_v2["eligible"] is False
    assert gate_forced_v2["mode"] == "OOS_TRADES_BLOCKED", f"Expected OOS_TRADES_BLOCKED, got {gate_forced_v2['mode']}"

    # 5. Diagnostic: What if V2 Score AND Trades passed (e.g. forced 55 trades)?
    print("\n--- 5. GATE ISOLATION 2 (If V2 >= 60 AND Trades >= 50) ---")
    gate_forced_trades = determine_paper_eligibility(
        strategy_quality=65.0,  # Simulate V2 pass
        signal_strength=70.0,
        directional_probability=60.0,
        directional_probability_sample=30,
        direction="UP",
        oos_sample_quality="OOS_SUFFICIENT",
        oos_trades=55,          # Simulate Trades pass
        oos_profit_factor=metrics["profit_factor"],
        oos_profit=metrics["profit"],
        robustness_status=robustness["status"]
    )
    print(f"Eligible:           {gate_forced_trades['eligible']}")
    print(f"Mode:               {gate_forced_trades['mode']}")
    print(f"Reason:             {gate_forced_trades['reason']}")

    assert gate_forced_trades["eligible"] is False
    assert gate_forced_trades["mode"] == "ROBUSTNESS_FRAGILE_BLOCKED", f"Expected ROBUSTNESS_FRAGILE_BLOCKED, got {gate_forced_trades['mode']}"

    print("\n" + "="*60)
    print("✅ ALL E2E GATE CHECKS PASSED")
    print("="*60)


if __name__ == "__main__":
    test_23_trade_fragile_sample()
