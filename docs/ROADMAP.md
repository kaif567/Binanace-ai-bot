# Roadmap — Current Status & Next Milestones

Last updated: 2026-09-16

---

## Current Live Status

| Item | Value |
|---|---|
| **Deployment** | `paper-baseline-v2` · commit `1526aff` · branch `item9-fixes-v2` |
| **VPS** | Oracle Cloud · Ubuntu · `binance-ai-bot.service` · zero crashes since 2026-09-03 |
| **Total predictions logged** | 394 |
| **Paper trades total** | 7 (mostly pre-v2) · net return: **-4.90%** |
| **New trades since v2 deploy** | 0 — gate correctly blocking (Strategy Quality 39–49, below 60 threshold) |

---

## Directional Probability Calibration Progress

| Direction | Decisive samples | Correct | Wrong | Neutral | Accuracy |
|---|---|---|---|---|---|
| **UP** | 35 / 50 | 13 | 22 | 134 | 37.14% |
| **DOWN** | 39 / 50 | 18 | 21 | 115 | 46.15% |

- Both directions currently show accuracy **below 50%** (no edge detected yet)
- Sample size is still small — full 50/50 calibration expected in **~2–3 days** from 2026-09-16
- Current below-50% trend is informative but not yet conclusive

---

## Completed Milestones (v2 Audit — All Deployed)

| # | Fix | Commit | Status |
|---|---|---|---|
| 1 | CLOSED_CANDLE_NEXT_CLOSED_CANDLE timing model | — | ✅ Deployed |
| 2 | Clean V3 prediction dataset, V1/V2 isolated | — | ✅ Deployed |
| 3 | Movement/noise threshold (fees + ATR-based) | — | ✅ Deployed |
| 4 | Realistic backtest execution (H/L TP/SL, SL-first, adverse gaps) | — | ✅ Deployed |
| 5 | Strategy Quality V2 formula (tanh-normalized, shrinkage) | `bfdd820` | ✅ Deployed |
| 6 | Training Score V2 (same formula, n+20 shrinkage) | `ae2b523` | ✅ Deployed |
| 7 | 5-condition paper-eligibility gate | — | ✅ Deployed |
| 8 | Directional Probability NEUTRAL-counting bug fix | `709dd38` | ✅ Deployed |

---

## Deliberately Deferred (Do Not Touch Without Approval)

### Untouched Final Holdout Data
- **What:** 10,000–20,000 candles + regime-diversity testing
- **Why deferred:** Reserved as a true holdout; using it now would contaminate the final evaluation
- **Planned use:** "Item 9 continuation" research phase, separate from live VPS baseline

### Symbol-Scoping Refactor
- **What:** Architectural changes needed before adding ETH/BNB/SOL/etc.
- **Why deferred:** Not needed until multi-coin is actually required
- **Prerequisite:** BTC paper-trading edge must be proven first

### Authenticated Binance Execution Layer
- **What:** Real order placement, signing, partial fill handling, reconciliation
- **Why deferred:** Real money only after paper edge is statistically proven
- **Prerequisite:** Full Phase 1 improvement validation on BTC

---

## Next Milestone: Full Calibration Statistical Evaluation

**Trigger:** Both UP and DOWN reach 50 decisive samples (expected ~2–3 days from 2026-09-16)

**Action:** Full statistical evaluation of directional edge
- If accuracy stays below/near 50%: confirms current model has no directional edge at this timeframe/indicator set → **proceed to Phase 1 improvements on single-coin BTC**
- If accuracy exceeds 55%+: indicates potential edge worth developing further → still validate Phase 1 improvements on BTC before any expansion

**Expected outcome (based on current trend):** No edge detected → proceed to Phase 1 improvements on BTC

> [!IMPORTANT]
> **Mandatory sequencing — no shortcuts:**
> 1. ✅ Both directions reach 50 decisive samples → statistical evaluation
> 2. → Phase 1 improvements tried on **single-coin BTC only** and re-validated
> 3. → Only after BTC single-coin edge is confirmed: consider multi-coin expansion
> 4. → Only after proven paper-trading edge at scale: consider live execution layer
>
> **Multi-coin expansion and live execution are NOT the next step.** Phase 1 on BTC is.  
> This order cannot be changed, reordered, or skipped — regardless of how long it takes.

---

## Phase 1 Improvements (Planned, Not Started)

These will be developed in a **new local branch**, fully tested, and validated **on single-coin BTCUSDT** before any VPS deployment. Multi-coin expansion only happens after Phase 1 edge is confirmed on BTC.

### 1. Multi-Timeframe (MTF) Confluence
- **Goal:** Require higher timeframe (4H, daily) trend alignment before taking a 1H signal
- **Logic:** A 1H UP signal only counts if 4H trend is also bullish
- **Expected benefit:** Filters false signals during choppy 1H action within a larger trend

### 2. ADX / Chop-Ranging Filter
- **Goal:** Block trades when ADX is below a threshold (e.g., ADX < 20–25)
- **Logic:** Low ADX = non-trending / ranging market = unreliable directional signals
- **Expected benefit:** Avoids the current problem of gate blocking due to low Strategy Quality in chop

### 3. SMC / Fair Value Gaps (FVG)
- **Goal:** Add Smart Money Concepts imbalance zones as a signal filter or confluence layer
- **Logic:** Only take trades that align with an unmitigated FVG (supply/demand imbalance)
- **Expected benefit:** Higher-probability entry points by requiring institutional-level structure

### Development Protocol for Phase 1
1. Implement one improvement at a time on a local dev branch
2. Run walk-forward backtest with the new filter — **on BTC data only**
3. Compare Strategy Quality V2 against current baseline
4. Full regression test suite must pass
5. Peer review the scoring/gate impact
6. Only after all three improvements are individually validated on BTC: consider combining them
7. Only after combined BTC validation: proceed to Phase 2 (multi-coin)
8. Deploy as a new frozen baseline (e.g., `paper-baseline-v3`)

---

## Future Phases (After Phase 1 Is Validated)

### Phase 2 — Multi-Coin Expansion
- Add ETH, BNB, or SOL only after BTC Phase 1 edge is proven
- Each new coin requires its own walk-forward validation
- Symbol-scoping refactor is a prerequisite

### Phase 3 — Live Execution
- Authenticated Binance order placement
- Partial fill reconciliation
- Position sizing and risk management for real capital
- Only after paper-trading edge is proven at production scale

---

## Rollback Reference

| Baseline | Tag | Commit | State |
|---|---|---|---|
| Current live | `paper-baseline-v2` | `1526aff` | Active on VPS |
| Previous | `paper-baseline-v1` | `253b96d` | Available for rollback |

To roll back on VPS:
```bash
git fetch --tags
git checkout paper-baseline-v1
sudo systemctl restart binance-ai-bot.service
```

