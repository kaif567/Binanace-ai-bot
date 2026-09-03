# Paper Baseline V2 — Deployment Summary

**Branch:** `item9-fixes-v2`  
**Tag:** `paper-baseline-v2` (pending approval)  
**Previous Baseline:** `paper-baseline-v1`  
**Date:** 2026-09-03

---

## ✅ Completed Fixes (Item 9 Audit)

### Finding #1: Strategy Quality Formula Saturation
**Status:** ✅ FIXED (commit `bfdd820`)

**Problem:** Old scoring formula used hard caps that created artificial ties and failed to differentiate near-neutral strategies.

**Solution:** Integrated Strategy Quality V2 formula:
- Component 1 (60%): Normalized return signal via `tanh(avg_return / 0.005)`
- Component 2 (40%): Normalized PF signal via `tanh(ln(PF) / ln(2.5))`
- Sample-size shrinkage: `n / (n + 50)` where n = OOS trades
- Range: 0-100 where 50 = neutral/no-edge
- Backwards-compatible alias preserved: `calculate_strategy_score = calculate_oos_strategy_quality`

**Files Modified:**
- `backtest/optimizer.py` (lines 123-213)
- `test_strategy_quality_v2.py` (new unit tests)

**Verification:** All tests pass, historical cases match expected values within ±0.5 pts.

---

### Finding #2: Training Optimizer Instability
**Status:** ✅ FIXED (commit `ae2b523`)

**Problem:** Different training burn-ins (100/200/300 candles) caused optimizer to flip between EMA strategies due to saturated training score formula creating artificial near-ties.

**Solution:** Integrated Training Score V2 formula:
- Component 1 (60%): Normalized return signal via `tanh(avg_return / 0.005)`
- Component 2 (40%): Normalized PF signal via `tanh(ln(PF) / ln(2.5))`
- Sample-size shrinkage: `n / (n + 20)` where n = closed trades (lower baseline than OOS)
- Range: 0-100 where 50 = neutral/no-edge
- Backwards-compatible alias preserved: `calculate_strategy_score = calculate_training_score`

**Files Modified:**
- `backtest/optimizer.py` (lines 25-120)
- `test_training_score_v2.py` (new unit tests)
- `compare_profitable_windows.py` (validation script)

**Verification:** Tested on 2024-03 profitable window — EMA pair selection stable at burn-ins 200/300 vs old formula's flip. Heavy shrinkage correctly applied to low-sample candidates (2-5 trades get 9-20% confidence).

---

### Finding #6: Directional Probability NEUTRAL-Counting Bug
**Status:** ✅ FIXED (commit `709dd38`)

**Problem:** `MIN_DIRECTIONAL_SAMPLES` (50) threshold counted CORRECT+WRONG+NEUTRAL outcomes to trigger "CALIBRATED" status. This allowed strategies to falsely show as calibrated when they had high NEUTRAL counts but insufficient decisive outcomes.

**Solution:** 
- Created `directional_outcomes = correct + wrong` variable for calibration threshold
- Changed calibration condition from `if sample >= MIN_DIRECTIONAL_SAMPLES` to `if directional_outcomes >= MIN_DIRECTIONAL_SAMPLES`
- Probability formula unchanged (NEUTRAL still correctly receives 0.5 credit in smoothed estimate)
- Added `directional_outcomes` to return dict for transparency

**Files Modified:**
- `database/confidence.py` (lines 220-238, 280-290, 313-318)
- `test_directional_probability_fix.py` (new unit tests)

**Verification:** Unit test confirms 6 correct + 0 wrong + 44 neutral = INSUFFICIENT_DATA (not CALIBRATED).

---

### Finding #1 + #2 Integration: 5-Condition Paper-Eligibility Gate
**Status:** ✅ INTEGRATED (commit `bfdd820`)

**Implementation:** Full sequential gate in `backtest/pipeline.py`:

1. **Strategy Quality V2 ≥ 60.0** — normalized OOS performance
2. **OOS Trades ≥ 50** — minimum sample size
3. **Robustness Check** — PF must stay ≥ 1.0 after removing top-1 and top-2 winners
4. **Market Score ≥ 65** (COLLECTION) or ≥ 70 (CALIBRATED) — favorable market conditions
5. **Signal Strength ≥ 65** (COLLECTION) or ≥ 70 (CALIBRATED) — high-confidence entry signal

**Modes:**
- `PAPER_COLLECTION_MODE` — when directional probability sample < 50
- `PAPER_EXECUTION_MODE` — when directional probability sample ≥ 50 (CALIBRATED)

**Files Modified:**
- `backtest/pipeline.py` (gate logic at lines 163-273)
- `test_e2e_gate.py` (end-to-end validation)
- `test_robustness_diagnostic.py` (outlier removal tests)

---

## 📊 Regression Test Results

**Final Suite (19 tests):** ✅ ALL PASSED

```
test_training_score_v2.py          7/7 PASSED  (V2 formula + edge cases + shrinkage)
test_strategy_quality_v2.py        4/4 PASSED  (OOS V2 formula + historical cases)
test_directional_probability_fix.py 3/3 PASSED  (Finding #6 calibration logic)
test_e2e_gate.py                   1/1 PASSED  (Full 5-condition gate)
test_robustness_diagnostic.py      4/4 PASSED  (Fragile/robust detection)
```

**Additional Regression:**
```
test_validation.py      ✅ Walk-forward produces training scores 64-68 (V2 working)
test_pipeline.py        ✅ Full pipeline integration intact
test_optimizer.py       ✅ Training optimizer uses V2 scoring
test_optimizer_advanced.py ✅ Advanced optimizer unchanged
test_risk.py            ✅ Risk analysis unchanged
test_scoring.py         ✅ Market scoring unchanged
test_indicators.py      ✅ Technical indicators unchanged
test_memory.py          ✅ Strategy memory SQLite logic intact
```

---

## 🚫 Deferred Items (Explicitly NOT Included)

### Finding #3: Final Untouched Holdout
**Status:** DEFERRED — data collection protocol, not code fix

**Rationale:** When new baseline v2 freezes, fresh live data collected after this point will naturally become the holdout. No code change needed now.

---

### Finding #4: Symbol-Scoping (Multi-Coin Support)
**Status:** DEFERRED — large multi-day refactor

**Scope:** Add symbol parameter to:
- V3 predictions (`database/confidence.py`)
- Paper trader (`monitor/paper_trader.py`)
- Strategy memory (`database/strategy_memory.py`)
- Walk-forward validation (`backtest/validation.py`)

**Rationale:** Currently BTC-only. When genuinely adding multi-coin support, dedicate proper time for full refactor. Not needed for current paper-baseline freeze.

---

### Finding #5: Authenticated Binance Execution Layer
**Status:** DEFERRED — new module for real-money execution

**Scope:** New module for:
- API authentication (API key, secret)
- Order placement (market/limit orders)
- Partial fill handling
- Reconciliation logic
- Idempotency checks

**Rationale:** Currently paper-mode only. Real-money execution requires dedicated implementation time and thorough testing. Not needed for paper-baseline freeze.

---

## 📦 Commits Since paper-baseline-v1

```
709dd38  Fix Directional Probability NEUTRAL-counting bug (Finding #6)
ae2b523  Integrate Training Score V2 formula (Finding #2)
bfdd820  Integrate Strategy Quality V2 formula + 5-condition gate (Finding #1)
1fed17b  Fix engine.py indent + add explicit signal override + trend utility
```

**Total:** 4 commits

---

## ⚠️ Known Limitations

1. **BTC-Only:** System currently hardcoded to BTCUSDT pair. Multi-coin support deferred (Finding #4).

2. **Paper-Mode Only:** No real Binance execution layer. Authenticated order placement deferred (Finding #5).

3. **Holdout Collection:** Final untouched holdout will be naturally created by live data collected AFTER v2 freeze. Not implemented yet (Finding #3).

4. **Training Score Shrinkage Baseline:** Training score uses `n/(n+20)` vs OOS `n/(n+50)` — this is intentional (training windows are shorter), but means training scores will typically be higher than OOS scores for same trade count.

5. **MIN_DIRECTIONAL_SAMPLES = 50:** Directional probability calibration requires 50 decisive outcomes (CORRECT+WRONG). Strategies may spend extended time in COLLECTION mode before reaching CALIBRATED status.

---

## 🚀 VPS Deployment Steps

### 1. Pre-Deployment Checklist

```bash
# Confirm branch and working tree
git status
# Output: On branch item9-fixes-v2, nothing to commit, working tree clean

# Verify all tests pass
python3 -m pytest test_training_score_v2.py \
  test_strategy_quality_v2.py \
  test_directional_probability_fix.py \
  test_validation.py \
  test_pipeline.py \
  test_e2e_gate.py \
  test_robustness_diagnostic.py -v
# Expected: 19 passed

# Run component tests
python3 test_optimizer.py
python3 test_optimizer_advanced.py
python3 test_risk.py
python3 test_scoring.py
python3 test_indicators.py
python3 test_memory.py
# Expected: All pass with Training Score V2 values (64-68 range)
```

### 2. Create Baseline Tag (AFTER USER APPROVAL)

```bash
# Tag the frozen baseline
git tag -a paper-baseline-v2 -m "Paper Baseline V2: Strategy Quality V2 + Training Score V2 + Directional Probability NEUTRAL-fix integrated. Item 9 Findings #1, #2, #6 completed. Findings #3, #4, #5 deferred."

# Push tag to remote
git push origin paper-baseline-v2

# Push branch
git push origin item9-fixes-v2
```

### 3. VPS Deployment (Preserve V1 Data)

```bash
# SSH into VPS
ssh user@vps-host

# Navigate to bot directory
cd /path/to/bot

# Backup v1 database files
mkdir -p backups/paper-baseline-v1
cp ai_decisions_v3.json backups/paper-baseline-v1/
cp strategy_memory.db backups/paper-baseline-v1/
cp *.log backups/paper-baseline-v1/

# Fetch and checkout v2
git fetch origin
git checkout paper-baseline-v2

# Verify tag
git describe --tags
# Output: paper-baseline-v2

# Install/update dependencies (if any changed)
pip install -r requirements.txt

# Restart bot service
sudo systemctl restart trading-bot
# OR: screen/tmux session restart

# Monitor logs
tail -f bot.log

# Verify v2 is running
grep "Strategy Quality V2" bot.log
grep "Training Score V2" bot.log
grep "directional_outcomes" bot.log
```

### 4. Post-Deployment Verification

```bash
# Check live monitor produces V2 scores
# Expected: Training scores in 50-70 range (V2 normalized)
# Expected: OOS scores use Strategy Quality V2 formula
# Expected: Directional probability shows "directional_outcomes" field

# Verify gate logic
# Expected: PAPER_COLLECTION_MODE when directional sample < 50
# Expected: 5-condition sequential gate blocks trades correctly
```

### 5. Rollback Procedure (If Needed)

```bash
# Checkout v1
git checkout paper-baseline-v1

# Restore v1 databases
cp backups/paper-baseline-v1/ai_decisions_v3.json .
cp backups/paper-baseline-v1/strategy_memory.db .

# Restart service
sudo systemctl restart trading-bot
```

---

## 📝 Notes for Future Work

1. **Holdout Collection (Finding #3):** After v2 freeze, any NEW live predictions logged to `ai_decisions_v3.json` should be tagged with `baseline_version: "v2"`. When enough accumulate, they become the untouched holdout for v3 validation.

2. **Multi-Coin Support (Finding #4):** When implementing, add `symbol` column to:
   - `ai_decisions_v3.json` prediction entries
   - `strategy_memory.db` strategies table
   - Walk-forward validation results
   - Paper trader state

3. **Real Execution (Finding #5):** When implementing authenticated Binance layer:
   - Use separate API keys for paper vs real mode
   - Implement idempotency (track `client_order_id`)
   - Handle partial fills (reconcile with order status endpoint)
   - Add order-level logging (separate from trade history)

4. **V3 Formula Considerations:** If data shows V2 still has saturation issues at extreme values (though tanh should prevent this), consider:
   - Wider tanh scaling factor (currently 0.005 for returns, ln(2.5) for PF)
   - Different shrinkage baseline (currently n+20 training, n+50 OOS)
   - Additional components (Sharpe ratio, max drawdown, etc.)

---

## ✅ Summary

**Ready for Production:** Yes, pending tag approval.

**Breaking Changes:** None. All changes are backwards-compatible (aliases preserved).

**Data Migration:** None required. Existing `ai_decisions_v3.json` and `strategy_memory.db` work unchanged.

**Performance Impact:** Negligible. V2 formulas are pure math (tanh, log) with no I/O.

**Risk Assessment:** Low. Extensive regression suite passes, formula changes are conservative (normalization, not architecture).

**Recommendation:** Deploy to VPS and monitor for 72 hours in paper-mode before considering real-money execution (when Finding #5 is eventually implemented).

---

**Awaiting Approval:** Ready to create `paper-baseline-v2` tag on user confirmation.
