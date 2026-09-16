# Binance AI Trading Bot — Paper-Trading Mode

> **⚠️ Paper-trading only. No real money is ever placed.**  
> Live symbol: **BTCUSDT · 1-hour candles** · Oracle Cloud VPS · systemd 24/7

---

## Overview

A Python-based algorithmic trading bot that uses technical indicators, a walk-forward backtesting engine, and a multi-metric eligibility gate to decide whether to open paper (simulated) LONG or SHORT positions on BTCUSDT.

The bot is designed with **statistical rigour first**: every threshold, formula, and gate condition exists for a concrete reason, and none of them are ever loosened just to force more trades or accelerate calibration.

---

## Current Deployment

| Item | Value |
|---|---|
| **Frozen baseline tag** | `paper-baseline-v2` |
| **Commit** | `1526aff` |
| **Branch** | `item9-fixes-v2` |
| **Rollback baseline** | `paper-baseline-v1` · commit `253b96d` |
| **VPS** | Oracle Cloud · Ubuntu · `binance-ai-bot.service` |
| **Uptime** | Zero crashes since 2026-09-03 |

---

## Quick-Start (local dev)

```bash
# 1. Create & activate venv
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the bot (paper mode, no real orders)
python main.py

# 4. Run the full test suite
pytest -v
```

---

## Project Layout

```
.
├── main.py                        # Entry point — starts live_monitor loop
├── backtest/
│   ├── engine.py                  # Core OHLCV backtest executor
│   ├── optimizer.py               # Walk-forward optimizer + Strategy/Training Score V2
│   ├── pipeline.py                # Full walk-forward pipeline orchestration
│   ├── validation.py              # OOS validation & robustness diagnostics
│   ├── risk.py                    # Position sizing, SL/TP calculations
│   ├── report.py                  # Human-readable result formatting
│   ├── monte_carlo.py             # Monte Carlo simulation utilities
│   └── strategy_runner.py        # Single-strategy execution wrapper
├── strategy/
│   └── scoring.py                 # Market scoring (STRONG BUY → FLAT direction)
├── indicators/
│   └── technical.py               # RSI, EMA, MACD, BB, ATR, ADX, volume via `ta`
├── scanner/
│   └── coins.py                   # Symbol list (currently BTCUSDT only)
├── monitor/
│   ├── live_monitor.py            # Main live loop — fetches candles, runs pipeline
│   └── paper_trader.py            # Paper-trade execution, atomic persistence, recovery
├── database/
│   ├── ai_log.py                  # Prediction logging (ai_decisions_v3.json)
│   ├── confidence.py              # Directional Probability calibration
│   ├── memory.py                  # Strategy memory (strategy_memory.db)
│   ├── paper_store.py             # Paper-trade persistence helpers
│   ├── performance.py             # Historical performance analytics
│   └── ...
├── ai_decisions_v3.json           # Clean V3 prediction dataset (live)
├── paper_trades.json              # Current open/closed paper trades
├── strategy_memory.db             # SQLite: walk-forward results cache
├── DEPLOYMENT_SUMMARY_V2.md       # Detailed v2 fix log & verification notes
└── docs/
    ├── ARCHITECTURE.md            # Full pipeline & data-flow diagram
    ├── SCORING.md                 # All 3 metrics + gate conditions + formulas
    ├── BACKTEST.md                # Walk-forward engine & execution model
    ├── WORKING_PRINCIPLES.md      # Rules that must never be violated
    └── ROADMAP.md                 # Live status, pending items, next milestones
```

---

## Documentation Index

| Doc | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | End-to-end pipeline, module responsibilities, data flow |
| [`docs/SCORING.md`](docs/SCORING.md) | Strategy Quality V2, Signal Strength, Directional Probability, 5-condition gate |
| [`docs/BACKTEST.md`](docs/BACKTEST.md) | Walk-forward design, execution model, SL/TP conflict rules |
| [`docs/WORKING_PRINCIPLES.md`](docs/WORKING_PRINCIPLES.md) | Non-negotiable development rules |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Current live status, pending work, next milestones |
| [`DEPLOYMENT_SUMMARY_V2.md`](DEPLOYMENT_SUMMARY_V2.md) | Per-fix audit trail for v2 baseline |

---

## Key Design Decisions (one-liner each)

- **Closed candles only** — open/unclosed candle never used for signals (eliminates look-ahead bias)
- **3 independent metrics** — Strategy Quality, Signal Strength, Directional Probability are computed separately and never blended into one score
- **Walk-forward, not fixed split** — expanding training window + non-overlapping OOS windows; optimizer never sees OOS data
- **tanh-normalized scoring** — raw dollar P&L / cumulative return replaced with normalized, shrinkage-weighted signals (scale-independent, saturation-proof)
- **Gate blocks, not nudges** — all 5 gate conditions must pass simultaneously; failing any one blocks the trade entirely
- **Statistical patience** — calibration thresholds, sample requirements, and gate scores are never lowered to force trades

---

*For the complete context narrative, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).*

