# Systematic Crypto Trading Strategy Research: A Rigorous Statistical Validation Study

### Overview
This project represents a comprehensive quantitative research effort to evaluate the predictive power of retail technical indicators and alternative data in the modern cryptocurrency market. Initially engineered as a live automated trading bot, it was rapidly pivoted into an institutional-grade validation engine. The ultimate outcome is a highly successful **negative-result study**: proving mathematically that over a dozen common trading approaches yield no statistically defensible edge when subjected to strict out-of-sample testing and real-world trading physics.

### What This Project Demonstrates
This repository showcases mature quantitative research and robust software engineering practices, prioritizing truth over "overfitting illusions." Key demonstrations include:
*   **Walk-Forward Validation:** Implementing a strict expanding-window training/testing pipeline to strictly isolate out-of-sample data.
*   **Look-Ahead Bias Proofing:** Defensive dataframe structuring (e.g., forced `.shift(1)` operations) ensuring algorithms cannot peak into future price data.
*   **Multi-Window & Multi-Coin Robustness:** Testing across 4.5 years of continuous BTC data (2020-2024), partitioned into 5 distinct macro-regimes (Bulls, Bears, Chop, Flash Crashes).
*   **Statistical Rigor & Confidence Intervals:** Replacing raw expected Profit Factor (PF) with Bootstrap Resampling and Monte Carlo simulations to generate 95% Confidence Intervals (CI). 
*   **ML Baseline Comparison:** Methodically validating a Logistic Regression linear baseline before attempting non-linear ensemble models (Random Forest), establishing a strict hierarchy of model evaluation.
*   **Production System Design:** A fully functioning deployment architecture complete with API pagination handling, state-synchronization (`latest_signal` safety), `systemd` daemon management, and a robust gap-execution paper-trading simulator.

### Methodology
1.  **Resilient Data Pipeline:** Fetched historical OHLCV, Alternative Data (Funding Rates, CVD / Taker Buy Volume) from Binance via robust, rate-limit-aware API wrappers.
2.  **Indicator Engine:** Calculated technical layers (EMA, Donchian, ATR, BBW, ADX) and merged them seamlessly with price data.
3.  **Walk-Forward Backtesting:** Iterated progressively through market data, training algorithms on historical windows and evaluating strictly on unseen future data.
4.  **Statistical Validation:** Filtered raw strategy returns through rigorous 95% CI thresholds, accepting only approaches whose lower-bound CI confirmed a >50% directional accuracy or >1.0 Profit Factor.
5.  **Results Synthesis:** Documented all outcomes transparently, analyzing *why* models failed in subsequent regimes.

### Key Finding (The 13-Hypothesis Reality Check)
**A rigorous negative-result:** We systematically tested 13 distinct approaches (10 Technical Indicator strategies, 2 Machine Learning models on alternative data, and 1 Non-Predictive Grid Trading algorithm) across multiple market regimes and assets. **None showed a statistically defensible edge** after accounting for realistic exchange fees (0.1% symmetric) and slippage (gap execution).

Rather than torturing the data to force a profitable backtest, this project documents the reality of highly efficient modern crypto markets: retail technical indicators and raw first-order alternative data possess zero inherent predictive edge on the 15m-4H horizons.

### Results Summary
| Approach Type | Strategy Tested | Core Finding |
| :--- | :--- | :--- |
| **Predictive (Technical)** | 1. EMA Trend-Following | Failed: Severe whipsaw losses in chop regimes. |
| **Predictive (Technical)** | 2. MTF (Multi-Timeframe) Confluence | Failed: Increased lag offset any precision gains. |
| **Predictive (Technical)** | 3. ADX/Chop Regime-Filtering | Failed: Regime changes happen faster than indicator latency. |
| **Predictive (Technical)** | 4. ATR-Fixed TP/SL | Failed: Static bounds easily hunted by market noise. |
| **Predictive (Technical)** | 5. ADX Regime-Gating | Failed: No statistical improvement over baseline. |
| **Predictive (Technical)** | 6. Donchian Breakout (Single-Coin) | Failed: Highly overfit to specific bull regimes. |
| **Predictive (Technical)** | 7. Trailing-ATR Exits | Failed: Tested 2.0x and 3.5x multipliers; both failed to establish a 95% CI lower-bound > 1.0 PF across distinct walk-forward windows. |
| **Predictive (Technical)** | 8. BBW-Squeeze Filters | Failed: Did not predict breakout *direction* accurately. |
| **Predictive (Technical)** | 9. Donchian Multi-Coin Portfolio | Failed: Strategies robust on BTC collapsed on ETH/SOL. |
| **Predictive (Technical)** | 10. RSI/BB Mean-Reversion | Failed: Caught falling knives during strong trends. |
| **Predictive (ML)** | 11. Logistic Regression (Alt-Data) | Failed: No linear separability (~31% out-of-sample precision). |
| **Predictive (ML)** | 12. Random Forest (Alt-Data) | Failed: No non-linear edge (~30-32% out-of-sample precision). |
| **Non-Predictive** | 13. Grid-Trading (Market Making) | Failed: Profitable in chop, but suffered massive tail-risk loss (-14.4%) in trend/crash breakouts. |

*For a full detailed writeup of the journey, methodology, and learnings, see [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md).*

### Tech Stack
*   **Languages:** Python 3.10+
*   **Data & Analysis:** `pandas`, `numpy`, `scipy` (Bootstrap CI)
*   **Machine Learning:** `scikit-learn` (Logistic Regression, Random Forest)
*   **APIs:** Binance Spot/Futures REST APIs
*   **Infrastructure:** Linux VPS, `systemd`, `cron` for data pipelines

### Skills Demonstrated
*   Statistical Rigor & Probability Testing
*   Overfitting Prevention (Walk-forward, OOS testing)
*   Production System Design & Resiliency
*   API Integration & Rate-Limit Handling
*   Quantitative Research Methodology
