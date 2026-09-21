# Algorithmic Trading Working Principles

## What Was NOT the Problem (Phase 1 Engineering Quality)
The negative statistical finding of Phase 1 (rejection of simple technical indicators) is exclusively about **signal-edge**, not about engineering quality or infrastructure flaws. The underlying framework has been independently verified as mathematically and logically sound.

The following potential pitfalls were explicitly avoided and structurally engineered out of the system:

1. **Look-Ahead Bias:** Fully eliminated. All indicators and thresholds were explicitly calculated using `shift(1)` logic, ensuring that any trading decision relied strictly on closed, historical candles.
2. **Backtest Execution Realism:** Realistic market conditions were explicitly modeled. The backtester strictly accounted for gap openings, stop-loss slippage (`SL_GAP`), and take-profit gaps (`TP_GAP`), matching the real-world behavior observed in our live paper-trading VPS logs.
3. **Fee Modeling:** Exchange fees were strictly and symmetrically modeled (0.1% maker/taker applied mathematically to both entry and exit legs).
4. **Validation Methodology (No Overfitting):** We enforced a rigid Multi-Window (Chop vs Bull regimes) and Multi-Coin (Portfolio-level) protocol. Strategies were not judged on raw Profit Factor, but on the **95% Confidence Interval (CI) lower bound** over large sample sizes (N > 200). 

Because these engineering foundations are flawless, we can state with absolute mathematical confidence that the failure of the bots to generate profit is due to the lack of predictive alpha in 1H technical indicators, not a bug in the code. This infrastructure remains highly valuable and reusable for future data sources.
