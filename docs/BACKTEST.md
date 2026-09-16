# Backtest Engine & Walk-Forward Design

This document describes the backtesting methodology, the walk-forward split strategy, and the realistic execution model used in the bot.

---

## Why Walk-Forward (Not Fixed Train/Test Split)

A single fixed train/test split suffers from:
- **Regime lock-in:** training on one market regime (e.g., 2021 bull) doesn't generalise to sideways/bear
- **Optimisation bias:** parameters tuned on one era look great on that era's OOS period but nowhere else
- **No confidence interval:** a single OOS result can be lucky

Walk-forward solves this by:
- Running many independent OOS evaluations across different market regimes
- Aggregating OOS results only (never mixing with training data) to compute Strategy Quality
- Exposing the optimizer to genuinely unseen data every fold

---

## Walk-Forward Structure

```
Full candle history (e.g., 3 years of 1h BTC):

Fold 1:  [=== Training ===|-- OOS --]
Fold 2:  [====== Training ======|-- OOS --]
Fold 3:  [========= Training =========|-- OOS --]
...
Fold N:  [=================== Training ===================|-- OOS --]

Training: expanding (each fold adds the previous OOS period to training)
OOS:      non-overlapping, fixed-length windows (e.g., 3 months each)
```

**Key invariant:** the optimizer is called only with training-window data. It never touches OOS data — not even to look at prices.

---

## Optimizer — Parameter Selection (Training Score V2)

For each training window, the optimizer evaluates candidate EMA pairs (and other parameters) and selects the best one using **Training Score V2**:

```python
c1 = tanh(avg_net_return / 0.005)           # normalised return component (60%)
c2 = tanh(log(PF) / log(2.5))              # normalised profit-factor component (40%)
shrinkage = n / (n + 20)                    # n = closed trades in training window
training_score = 50 + 50 * (0.6*c1 + 0.4*c2) * shrinkage
```

### Why shrinkage matters for optimizer stability
Before Training Score V2, the old formula used raw cumulative P&L with caps, causing artificial near-ties between candidates. Even tiny differences in how many burn-in candles were used (100 vs 200 vs 300) caused the optimizer to flip between EMA pairs unpredictably.

With V2 shrinkage (n/(n+20)), a 5-trade candidate gets ~20% confidence — it simply cannot beat a 50-trade candidate with slightly lower per-trade return. This eliminated the burn-in instability.

---

## Engine Execution Model (`backtest/engine.py`)

### Entry timing
- Signal generated on **closed candle N**
- Entry fills at **open of candle N+1** (next candle)
- This mirrors the live bot's actual execution timing

### SL / TP checking
- Both SL and TP are checked against the candle's **high** and **low** (not just close)
- This is the realistic approximation — price moves within the candle are not known exactly, but H/L bounds are known

### SL-first conflict rule
If the same candle's price range touches **both** the SL level and the TP level:
- **SL is applied** (conservative)
- Rationale: in a real fast market, adverse moves often come first; assuming TP fills in a conflicted candle overstates performance

### Adverse gap handling
If a candle **opens** beyond the SL level (gap open against the position):
- Exit is filled at the **SL price** (not the gap-open price)
- Rationale: stop orders in live markets would trigger at the SL order level, not at an arbitrary gap price (within normal market conditions)

### Fee application
```
net_return = gross_return - (entry_fee + exit_fee)
```
Default: Binance-standard maker/taker rates applied to both entry and exit.

---

## Prediction Timing Model

```
Hour H:00  →  Candle H-1 closes  →  Signal generated (UP/DOWN/FLAT)
                                      Prediction logged: target = candle H close price

Hour H:00  →  Entry fills at candle H open

Hour H+1:00 →  Candle H closes   →  Outcome resolved: CORRECT / WRONG / NEUTRAL
```

**Fixed 60-minute prediction horizon.** The signal always predicts the direction of the *next* 1-hour candle.

This was locked in as the **CLOSED_CANDLE_NEXT_CLOSED_CANDLE timing model** in v2 after fixing an earlier bug where the prediction horizon was ambiguous.

---

## OOS Aggregation → Strategy Quality V2

After all folds complete, their OOS results are pooled:

```
all_oos_trades = [fold_1_oos_trades] + [fold_2_oos_trades] + ... + [fold_N_oos_trades]

avg_net_return = mean(net_return per trade) across all_oos_trades
PF = sum(winning_returns) / abs(sum(losing_returns))
n = len(all_oos_trades)

strategy_quality = 50 + 50 * (0.6 * tanh(avg_net_return/0.005)
                             + 0.4 * tanh(ln(PF)/ln(2.5))) * n/(n+50)
```

This gives a single score representing aggregate OOS robustness across all tested market regimes.

---

## Robustness Diagnostic

After computing Strategy Quality, the robustness diagnostic checks whether the edge is concentrated in outlier trades:

```python
# Sort OOS trades by net return (best first)
sorted_trades = sorted(all_oos_trades, key=lambda t: t.net_return, reverse=True)

# Check PF after removing top-1
remaining = sorted_trades[1:]
pf_minus_1 = profit_factor(remaining)

# Check PF after removing top-2
remaining = sorted_trades[2:]
pf_minus_2 = profit_factor(remaining)

if pf_minus_1 < 1.0 or pf_minus_2 < 1.0:
    diagnostic = "FRAGILE"
else:
    diagnostic = "ROBUST"
```

A `FRAGILE` result blocks the trade at gate condition #5.

---

## Monte Carlo Simulation (`backtest/monte_carlo.py`)

Used for additional confidence estimation by resampling OOS trade sequences. Not part of the gate — used for research and reporting purposes only.

---

## Legacy vs V3 Data Isolation

| Dataset | Status | Used for calibration |
|---|---|---|
| `ai_decisions.json` (V1) | Legacy — different timing model | ❌ No |
| `ai_decisions_v2.json` (V2) | Legacy — pre-fix predictions | ❌ No |
| `ai_decisions_v3.json` (V3) | Live — post v2-deploy, clean | ✅ Yes |

V1 and V2 datasets are preserved for reference but are completely isolated from any calibration or scoring computation. Mixing them would introduce historical bias from the pre-fix era.

---

## Test Coverage

| Test file | What it covers |
|---|---|
| `test_backtest.py` | Basic engine correctness |
| `test_advanced_backtest.py` | Edge cases: gap opens, SL/TP conflicts |
| `test_item4_execution.py` | Realistic execution model (high/low, SL-first) |
| `test_strategy_quality_v2.py` | Strategy Quality V2 formula & known historical values |
| `test_training_score_v2.py` | Training Score V2 stability across burn-in configs |
| `test_robustness_diagnostic.py` | FRAGILE/ROBUST classification |
| `test_burnin_instability.py` | Regression: optimizer no longer flips between EMA pairs |
| `test_item8_paper_execution.py` | Paper trade execution, fee/SL, atomic persistence |
| `test_e2e_gate.py` | Full 5-condition gate integration |
| `test_directional_probability_fix.py` | NEUTRAL-counting fix regression |

