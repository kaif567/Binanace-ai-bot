# Working Principles — Non-Negotiable Rules

These rules govern all development on this codebase. They exist to protect the statistical validity of the paper-trading experiment. **No exception is acceptable without a documented, independently-reviewed justification.**

---

## Rule 1 — Never Lower Thresholds to Force Trades

> **The single most important rule.**

The following thresholds, requirements, and formulas are **permanently fixed**. They must **never** be lowered or modified to generate faster trades or accelerate calibration — **no matter how long it takes, no matter how long the bot sits idle, no matter how sideways the market is:**

| Parameter | Fixed value | What it guards |
|---|---|---|
| Strategy Quality V2 gate | **≥ 60.0** | OOS edge above neutral (50 = no edge) |
| OOS trades requirement | **≥ 50 trades** | Minimum sample for statistical confidence |
| Profit Factor gate | **≥ 1.20** | Gross wins must meaningfully exceed losses |
| Avg net return per trade gate | **> 0** | Net-of-fees edge must be positive |
| Robustness check | **≠ FRAGILE** | Edge must not depend on 1–2 outlier trades |
| Calibration sample requirement | **≥ 50 decisive samples per direction** | Sufficient accuracy estimate (NEUTRAL excluded from count) |
| Scoring formula parameters | **tanh scale 0.005, PF ref 2.5, shrinkage n+50/n+20** | Scale-independent, saturation-proof scoring |

**No exception is acceptable** — not for speed, not for convenience, not because the market is being uncooperative. Lowering any of these thresholds invalidates the entire statistical validation process.

### Why calibration and gate blocking are correct, not problems
- Bot hasn't traded since v2 deploy (2026-09-03): **correct** — Strategy Quality is 39–49 in choppy market, below the 60 threshold. The gate is working.
- Calibration taking days: **correct** — 50 decisive samples per direction at ~1 signal/hour takes the time it takes. Neutral outcomes (market noise) do not count toward the 50.
- Both directions below 50% accuracy: **informative, not alarming** — sample size is still small; no conclusion yet.

### Specific shortcuts that were explicitly considered and REJECTED

| Rejected shortcut | Reason rejected |
|---|---|
| Lower Strategy Quality gate: 60 → 50 | 50 = neutral (no edge). Trading at 50 = random |
| Lower OOS trade requirement: 50 → 20 | Insufficient sample; strategy score is unreliable |
| Lower calibration threshold: 50 → 30 decisive | Too few samples; accuracy estimate noisy |
| Count NEUTRAL toward the 50-sample target | Creates false CALIBRATED status; pre-v2 bug now fixed |
| Tighten neutral zone to get more decisive samples | Inflates accuracy by classifying noise as signal |
| Switch to 15-min candles for faster data | Changes the strategy entirely; needs fresh validation |
| Add ETH/BNB/SOL now for more signal volume | Multi-coin edge ≠ BTC edge; needs separate validation |

---

## Rule 2 — No Changes to Live VPS Without Explicit Approval

The live deployment on Oracle Cloud is a **frozen baseline** (`paper-baseline-v2`, tag `paper-baseline-v2`, commit `1526aff`).

**Development workflow:**
1. All dev work happens locally in a **separate branch**
2. Changes are tested fully (regression suite must pass)
3. A detailed diff and plan is reviewed and approved
4. Only then is a new frozen baseline deployed and tagged

**Never** push directly to the live VPS branch or edit files on the VPS without a tagged release.

**Rollback:** `paper-baseline-v1` (commit `253b96d`) is available if needed.

---

## Rule 3 — Plan Before Code

Before writing any code, always present:
1. **Which files** will be modified (with line ranges if possible)
2. **What exactly** will change and why
3. **What tests** will be added or updated
4. **What regressions** could be introduced

Wait for explicit approval before proceeding to implementation.

---

## Rule 4 — Complete File Content in One Response

When delivering code changes:
- Always provide the **complete updated file** in a single response
- Never say "I'll send the rest in the next message"
- Never provide partial diffs that require the user to mentally merge

---

## Rule 5 — Validate Against Real Historical Data

When testing a new formula or scoring change:
- Identify **real historical data points** (specific backtest runs, known candle ranges)
- Compute expected outputs manually or with a reference script
- Verify the implementation matches within an acceptable tolerance (e.g., ±0.5 pts for scores)
- **Never use synthetic or fabricated numbers** as the primary validation evidence

Example: Strategy Quality V2 was validated against the 23-trade fragile sample (expected: ~58, old formula: 83.91) and the March 2024 profitable window before being merged.

---

## Rule 6 — Full Regression Suite Must Pass

After any change, run the **full test suite** and confirm all tests pass:

```bash
pytest -v
```

If a test breaks, it must be either:
- **Fixed** (because the new behaviour is correct and the test was outdated), or
- **Understood** (with a documented reason for the test change)

Never suppress or delete a failing test without understanding why it failed.

---

## Rule 7 — Show Diffs for Review

When presenting code changes for approval:
- Show a clear diff (old vs new) for all modified code sections
- Highlight the specific lines that change the behaviour (not just refactoring)
- Include the test changes in the same diff

---

## Rule 8 — Statistical Patience

The calibration process takes as long as it takes. The bot is designed to:
- Wait for 50 decisive UP samples before UP is CALIBRATED
- Wait for 50 decisive DOWN samples before DOWN is CALIBRATED
- Block trades when Strategy Quality is below 60

**This waiting is correct behaviour, not a bug.** The current live state (both directions below 50 decisive samples, gate blocking trades) is the system working as designed in a choppy/sideways market.

---

## Rule 9 — Multi-Coin Only After BTC Edge Is Proven

The planned sequence:
1. Prove (or disprove) a real directional edge on BTCUSDT
2. If edge exists: validate Phase 1 improvements (MTF, ADX filter, SMC/FVG) still on BTC
3. Only after BTC edge is re-validated: consider ETH, BNB, etc.

Adding coins prematurely to get more data faster defeats the purpose of the BTC-first validation.

---

## Rule 10 — Real Execution Layer Is Deferred

The authenticated Binance order placement layer (real signing, partial fills, reconciliation) is **intentionally deferred** until:
- Paper-trading edge is statistically proven
- Phase 1 improvements are validated
- A separate review of execution risk, key management, and order reconciliation is done

No real-money execution code should be written or deployed until this milestone is explicitly reached and approved.

