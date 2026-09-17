# Roadmap — Current Status & Next Milestones

Last updated: 2026-09-17

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
| **UP** | 39 / 50 | — | — | — | Pending full count |
| **DOWN** | 46 / 50 | — | — | — | Pending full count |

- Both directions nearing 50-sample threshold — verdict expected very soon
- Current trend: accuracy below 50% on both directions (no edge detected yet)

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
| — | SQ V2 / Robustness standalone reporting fix | `5434ff6` | ✅ Local (tooling only, not deployed) |

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

**Trigger:** Both UP and DOWN reach 50 decisive samples (imminent — UP: 39/50, DOWN: 46/50)

**Action:** Full statistical evaluation of directional edge
- If accuracy stays below/near 50%: confirms current model has no directional edge at this timeframe/indicator set → **decide jointly on next Phase 1 approach**
- If accuracy exceeds 55%+: indicates potential edge worth developing further → still validate Phase 1 improvements on BTC before any expansion

> [!IMPORTANT]
> **Mandatory sequencing — no shortcuts:**
> 1. ✅ Both directions reach 50 decisive samples → formal written verdict
> 2. → Phase 1 improvements tried on **single-coin BTC only**, using the multi-window design process (see below)
> 3. → Only after BTC single-coin edge is confirmed: consider multi-coin expansion
> 4. → Only after proven paper-trading edge at scale: consider live execution layer
>
> **Multi-coin expansion and live execution are NOT the next step.**  
> This order cannot be changed, reordered, or skipped — regardless of how long it takes.

---

## Phase 1 Improvements — ⚠️ INCOMPLETE / INCONCLUSIVE

> [!CAUTION]
> **Phase 1 status: INCOMPLETE.** Two filter attempts were made and fully reverted after failing
> multi-window validation. Codebase is back to clean `paper-baseline-v2` + SQ V2 reporting fix.
> No filter code is deployed or active on the VPS.

### What Was Attempted and Why It Failed

#### Attempt 1: MTF Confluence (EMA 20/50 on 4H) — REVERTED

| Window | PF Before | PF After | Verdict |
|---|---|---|---|
| Jan 2024 (dev window) | 0.76 | 1.30 | ✅ Looked good |
| Mar 2024 | 0.77 | 0.50 | ❌ FAIL |
| Aug 2023 | 1.23 | 0.52 | ❌ FAIL |

**Diagnosis:** Overfitted to Jan 2024 trending conditions.

#### Attempt 2: Chop Filter / ADX+ATR Regime Filter (Part A) — REVERTED

| Window | PF Before | PF After | SQ V2 Before | SQ V2 After | Verdict |
|---|---|---|---|---|---|
| Aug 2023 (sweep-adjacent) | 0.44 | 0.36 | 45.34 | 44.40 | ✅ Neutral |
| Jan 2024 | 1.09 | 0.59 | 52.49 | 41.93 | ❌ FAIL |
| Mar 2024 | 1.09 | 0.61 | 53.57 | 38.59 | ❌ FAIL |

**Diagnosis:** Same single-window overfitting pattern. Thresholds from sweep did not generalize.

### Lesson Learned — Mandatory Future Protocol

> [!IMPORTANT]
> **Any future threshold-based filter MUST follow a multi-window design process from day one.**
> Single-window "it worked!" is not sufficient evidence. Both attempts passed single-window review
> and failed multi-window validation. This methodology is now mandatory:
>
> 1. Define filter logic concept — no thresholds yet
> 2. Fetch data from **≥3 structurally different windows** upfront (before any parameter choice)
> 3. Define pass/fail criteria before running numbers
> 4. Select thresholds that generalize across ALL windows simultaneously — not per-window best
> 5. Only if step 4 succeeds: implement in code + run full regression suite

### What Comes Next (After Phase 0 Verdict)

Once Phase 0 calibration completes (UP: 39/50, DOWN: 46/50 — imminent), we decide jointly:

- **Option A:** Attempt a third filter using a structurally different approach — but only if designed multi-window from the start per protocol above
- **Option B:** Accept that threshold-based filters may not generalize on this strategy/data; consider a fundamentally different approach to improving edge
- **Option C:** If Phase 0 verdict shows directional accuracy has shifted meaningfully, reassess whether Phase 1 filter work is even the right priority

**No Phase 1 filter code will be written until this joint decision is made.**

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

