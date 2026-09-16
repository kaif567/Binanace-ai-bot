# Scoring & Gate System

This document covers all three independently-computed metrics, their formulas, the 5-condition paper-eligibility gate, and the historical rationale for each design decision.

---

## Overview — Three Independent Metrics

The bot never blends its metrics into one composite score. Each metric answers a different question:

| Metric | Question | Source |
|---|---|---|
| **Strategy Quality V2** | Does the strategy have an OOS-proven edge? | Walk-forward backtest results |
| **Signal Strength** | How strongly do current indicators point in this direction? | Current candle snapshot |
| **Directional Probability** | Has the bot's live V3 prediction been correct historically? | `ai_decisions_v3.json` outcomes |

All three must independently satisfy gate conditions before a trade is opened.

---

## 1. Strategy Quality V2

Measures the robustness of the strategy's out-of-sample (OOS) performance across all walk-forward folds.

### Formula

```
component_1 = tanh(avg_net_return_per_trade / 0.005)    # return signal, 60% weight
component_2 = tanh(ln(PF) / ln(2.5))                    # profit-factor signal, 40% weight
shrinkage   = n / (n + 50)                               # confidence, n = OOS trade count
strategy_quality = 50 + 50 × (0.6×c1 + 0.4×c2) × shrinkage
```

### Properties
- **Range:** 0 – 100
- **Neutral (no edge):** 50
- **Strong edge:** approaches 100
- **Scale-independent:** tanh normalises; a strategy with avg_return=0.5% and PF=1.4 scores the same regardless of how many dollars were traded
- **Shrinkage:** with n=50 OOS trades, confidence = 50%; with n=200, confidence = 80%

### Why this replaced the old formula
The old formula used raw cumulative OOS dollar profit, which caused:
- **Score saturation** — more trades always meant higher score, even if edge/trade was tiny
- **Scale dependence** — score changed with position size, not strategy quality
- **Fragile small samples** — a 23-trade sample with lucky outliers scored 83.91/100; the V2 formula correctly scores it ~58

### Gate condition
```
Strategy Quality V2 >= 60.0
```

---

## 2. Signal Strength

Measures how strongly the current indicator snapshot aligns with the predicted direction (UP or DOWN).

### Computation
Each indicator casts a directional vote with a weight:
- Bullish vote → positive contribution
- Bearish vote → negative contribution
- Neutral → zero contribution

Weighted sum normalised to 0–100, where:
- 0 = maximum bearish alignment
- 50 = mixed / no alignment
- 100 = maximum bullish alignment

When the predicted direction is DOWN, the score is mirrored (100 − raw_score).

### Gate condition
```
Signal Strength is used as supporting context.
Its specific gate threshold is checked in the 5-condition gate below.
```

---

## 3. Directional Probability

Measures the bot's actual live prediction accuracy, stratified by direction (UP vs DOWN).

### How outcomes are classified

Every closed prediction (candle N+1 close vs predicted direction) is classified as:

| Class | Condition |
|---|---|
| **CORRECT** | Move ≥ noise threshold AND matches predicted direction |
| **WRONG** | Move ≥ noise threshold AND opposes predicted direction |
| **NEUTRAL** | Move < noise threshold (fees + ATR-based — too small to matter) |

**Noise threshold** = estimated round-trip fee cost + ATR-scaled minimum meaningful move.  
This prevents tiny market microstructure noise from inflating or deflating accuracy.

### Calibration logic
```python
directional_outcomes = correct + wrong      # NEUTRAL excluded
if directional_outcomes >= MIN_DIRECTIONAL_SAMPLES (50):
    status = "CALIBRATED"
    accuracy = correct / directional_outcomes   # conditional accuracy
else:
    status = "PENDING"
```

> **Critical:** NEUTRAL outcomes are **excluded** from the calibration threshold count.  
> A prediction log with 130 NEUTRAL + 35 decisive samples is still PENDING (35 < 50).  
> This was a bug in pre-v2 code (counting NEUTRAL toward the 50 threshold) — now fixed.

### Separate calibration per direction
UP and DOWN are calibrated independently. Both must reach CALIBRATED status for the gate to consider Directional Probability.

### Gate condition
```
Directional Probability metric used as context; gate relies on OOS trades count (see gate below).
```

---

## 4. Robustness Diagnostic

A fragility check run after computing Strategy Quality V2.

### Logic
1. Sort OOS trades by net return (descending)
2. Remove the single best trade → recompute PF. If PF < 1.0 → **fragile flag set**
3. Remove the two best trades → recompute PF. If PF < 1.0 → **fragile flag set**

If either check fails → diagnostic result = `FRAGILE`.

### Gate condition
```
Robustness diagnostic != FRAGILE
```
A strategy that collapses when its top 1–2 trades are removed is relying on outliers, not a real edge.

---

## 5. The Five-Condition Paper-Eligibility Gate

**All five conditions must pass simultaneously.** Failing any one blocks the trade.

| # | Condition | Rationale |
|---|---|---|
| 1 | `Strategy Quality V2 >= 60.0` | OOS edge proven above neutral (50) by meaningful margin |
| 2 | `OOS trades >= 50` | Minimum sample for statistical confidence; shrinkage already penalises low-n |
| 3 | `Profit Factor >= 1.20` | Gross wins must meaningfully exceed gross losses (not just break even) |
| 4 | `Avg net return per trade > 0` | After fees and slippage, the strategy must be net positive |
| 5 | `Robustness diagnostic != FRAGILE` | Edge must not depend on 1–2 lucky outlier trades |

### Current live gate behaviour
Since `paper-baseline-v2` was deployed (2026-09-03), the gate has **correctly blocked all new trades** because Strategy Quality has stayed in the 39–49 range during the current choppy/sideways BTC market. This is **expected and correct behaviour** — the gate is doing its job.

---

## Formula Quick Reference

```
# Strategy Quality V2 (and Training Score V2 — same formula, different shrinkage)
c1 = tanh(avg_net_return / 0.005)
c2 = tanh(ln(max(PF, 1e-9)) / ln(2.5))
shrinkage_oos      = n / (n + 50)    # Strategy Quality: n = OOS trades
shrinkage_training = n / (n + 20)    # Training Score:   n = training closed trades
score = 50 + 50 * (0.6*c1 + 0.4*c2) * shrinkage

# Directional Probability
decisive = correct + wrong           # NEUTRAL excluded
accuracy = correct / decisive        # only when decisive >= 50

# Robustness
PF_minus_1 = gross_wins_excluding_top1 / gross_losses_excluding_top1
PF_minus_2 = gross_wins_excluding_top2 / gross_losses_excluding_top2
FRAGILE if PF_minus_1 < 1.0 or PF_minus_2 < 1.0
```

---

## What Was Deliberately Rejected

The following changes were explicitly considered and rejected to protect statistical integrity:

| Rejected change | Why rejected |
|---|---|
| Lower Strategy Quality gate from 60 to 50 | 50 = neutral/no-edge; lowering = trading with no proven edge |
| Lower OOS trade requirement from 50 | Insufficient sample for statistical confidence |
| Count NEUTRAL toward calibration threshold | Would allow false "CALIBRATED" status with high neutral rates |
| Tighten neutral zone to get more decisive samples | Would inflate accuracy by miscounting noise trades |
| Add coins prematurely to get more data faster | Multi-coin needs separate validation; BTC edge ≠ ETH edge |
| Change from 1-hour to 15-min candles | Changes the entire strategy; needs fresh validation from scratch |

