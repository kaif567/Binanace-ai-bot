# Architecture — End-to-End Pipeline

This document describes every stage of the bot's data pipeline, the responsibilities of each module, and how data flows from the Binance API through to a paper trade decision.

---

## High-Level Pipeline

```
Binance API (REST)
        │
        ▼
  Fetch OHLCV candles  ──── CLOSED candles only (look-ahead bias prevention)
        │
        ▼
  Technical Indicators  ─── RSI · EMA20/50 · MACD · Bollinger Bands
  (indicators/technical.py)    ATR · ADX · Volume avg  (via `ta` library)
        │                      All causal / non-leaking calculations
        ▼
  Market Scoring        ─── Converts indicator state → direction signal
  (strategy/scoring.py)        STRONG BUY / BUY / HOLD / SELL / STRONG SELL
                               → UP / DOWN / FLAT
        │
        ▼
  Walk-Forward Backtest ─── Expanding training window (optimizer sees only train data)
  (backtest/pipeline.py)       Non-overlapping OOS test windows
  (backtest/optimizer.py)      Candidate strategy selection via Training Score V2
  (backtest/engine.py)         Realistic execution: high/low TP/SL, SL-first conflict rule
        │
        ▼
  3 Independent Metrics ─── Strategy Quality V2  (OOS robustness)
  (backtest/validation.py)     Signal Strength      (current indicator state)
  (database/confidence.py)     Directional Prob.    (live V3 prediction outcomes)
        │
        ▼
  5-Condition Gate      ─── ALL 5 conditions must pass simultaneously
  (monitor/live_monitor.py)    Failing any one → trade blocked
        │
        ▼
  Paper Trade Execution ─── LONG or SHORT opened
  (monitor/paper_trader.py)    Fees applied · SL slippage simulated
                               Atomic JSON persistence · crash-recovery
        │
        ▼
  Prediction Logging    ─── Every signal logged to ai_decisions_v3.json
  (database/ai_log.py)         Outcome resolved on candle close
  (database/confidence.py)     Feeds Directional Probability calibration
```

---

## Module Responsibilities

### `main.py`
Entry point. Initialises the live monitor loop, handles graceful shutdown signals.

---

### `indicators/technical.py`
Computes all technical indicators from raw OHLCV data using the `ta` library.

| Indicator | Purpose |
|---|---|
| RSI (14) | Momentum / overbought-oversold |
| EMA 20 / 50 | Trend direction (walk-forward optimized pair) |
| MACD | Trend momentum confirmation |
| Bollinger Bands | Volatility / price extremes |
| ATR (14) | Volatility measurement — used in SL sizing & noise threshold |
| ADX (14) | Trend strength — distinguishes trending vs ranging |
| Volume avg | Relative volume context |

> **Causal guarantee:** all indicators are computed on the closed-candle series. No future data leaks into any indicator window.

---

### `strategy/scoring.py`
Converts the indicator snapshot into a single direction signal.

**Scoring logic:**
- Each indicator contributes a weighted vote (BULLISH / BEARISH / NEUTRAL)
- Aggregated score mapped to: `STRONG BUY` · `BUY` · `HOLD` · `SELL` · `STRONG SELL`
- Direction output: `UP` (strong/moderate buy) · `DOWN` (strong/moderate sell) · `FLAT` (hold)

---

### `backtest/engine.py`
Core OHLCV backtest executor. Simulates trade entries and exits on historical candles.

**Execution model (v2 — realistic):**
- Entry: at open of the candle *after* the signal candle closes (no look-ahead)
- SL / TP checked against candle **high and low** (not just close)
- **SL-first conflict rule:** if the same candle touches both SL and TP, SL is applied (conservative)
- **Adverse gap handling:** gaps that open beyond SL are filled at SL price
- Fees applied per trade (configurable, default Binance maker/taker)

---

### `backtest/optimizer.py`
Walk-forward parameter optimizer. Selects the best EMA pair (and other parameters) for each training window.

**Training Score V2** (used to rank candidates during training):
```
component_1 = tanh(avg_net_return / 0.005)          # 60% weight, normalized return
component_2 = tanh(ln(PF) / ln(2.5))                # 40% weight, normalized profit factor
shrinkage   = n / (n + 20)                           # n = closed trades in training window
training_score = 50 + 50 × (0.6×c1 + 0.4×c2) × shrinkage
```
Range: 0–100, neutral/no-edge = 50. Shrinkage prevents low-sample candidates from ranking highly.

---

### `backtest/pipeline.py`
Orchestrates the full walk-forward sequence:
1. Slice training + OOS windows from the full candle history
2. Run optimizer on training window → best parameters
3. Run engine on OOS window with those parameters → OOS results
4. Aggregate results → feed to validation

---

### `backtest/validation.py`
Computes **Strategy Quality V2** from OOS results and runs the robustness diagnostic.

**Strategy Quality V2:**
```
component_1 = tanh(avg_net_return_per_trade / 0.005)   # 60% weight
component_2 = tanh(ln(PF) / ln(2.5))                   # 40% weight
shrinkage   = n / (n + 50)                              # n = OOS trades
strategy_quality = 50 + 50 × (0.6×c1 + 0.4×c2) × shrinkage
```

**Robustness diagnostic:**
- Remove top-1 winning trade → check if PF ≥ 1.0
- Remove top-2 winning trades → check if PF ≥ 1.0
- If either check fails → `FRAGILE` (gate blocks trade)

---

### `backtest/risk.py`
Position sizing and SL/TP distance calculations. ATR-based stop-loss sizing.

---

### `strategy/scoring.py` → Signal Strength
The same scoring module also exports a **Signal Strength** value (0–100) representing how strongly the current indicator state aligns with the predicted direction.

---

### `database/confidence.py`
Tracks live V3 prediction outcomes to compute **Directional Probability**.

**Calibration logic:**
- Every closed prediction is classified: CORRECT / WRONG / NEUTRAL
- NEUTRAL = movement within `fees + ATR-based noise threshold` (too small to count)
- Calibration triggers only when `correct + wrong ≥ 50` (NEUTRAL excluded from count)
- Accuracy = `correct / (correct + wrong)` — conditional on decisive outcome

---

### `monitor/live_monitor.py`
Main live loop. Runs every completed 1-hour candle. Orchestrates:
1. Fetch closed candles from Binance
2. Compute indicators
3. Run walk-forward pipeline
4. Evaluate all 3 metrics
5. Check 5-condition gate
6. If gate passes → call paper_trader
7. Log prediction to ai_decisions_v3.json

---

### `monitor/paper_trader.py`
Executes simulated trades. Handles:
- LONG / SHORT entry at next candle open
- Fee deduction
- SL slippage simulation
- Atomic write to `paper_trades.json` (crash-safe)
- On-startup recovery: reconciles any open trades that may have closed during downtime

---

## Data Files

| File | Purpose |
|---|---|
| `ai_decisions_v3.json` | Live clean prediction log (V3 format, post-v2 deploy) |
| `ai_decisions_v2.json` | Legacy V2 predictions (isolated, not used for calibration) |
| `ai_decisions.json` | Legacy V1 predictions (isolated, not used for calibration) |
| `paper_trades.json` | Current open/closed paper trade state |
| `strategy_memory.db` | SQLite cache of walk-forward backtest results |

---

## Closed-Candle Timing Model

```
Candle N closes at  T+00:00
  │
  ├─ Indicators computed on candles 0..N  (all closed)
  ├─ Signal generated: UP / DOWN / FLAT
  ├─ Prediction logged with target = close(N+1)
  │
Candle N+1 opens at T+00:00  ← entry fills here (next open)
  │
Candle N+1 closes at T+01:00 ← outcome resolved here (fixed 60-min horizon)
```

This model eliminates look-ahead bias: the signal is generated *after* candle N is fully closed, and entry is at the *next* candle's open price.

