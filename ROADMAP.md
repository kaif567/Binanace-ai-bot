# Crypto Algorithmic Trading Bot Roadmap

## Phase 1: Concluded — No Statistical Edge Found (1H Timeframe)
**Status:** Completed & Rejected (Null Hypothesis Confirmed)

### Summary of Findings
Extensive, rigorous testing was conducted over a series of 10 incremental methodology iterations to determine if simple technical indicators provide a statistically significant edge in the crypto market. 

All tested methodologies were rigorously evaluated using expanding multi-window tests (Chop vs Bull regimes) and strict 95% Confidence Interval (CI) bounds for sample sizes (N > 200). 

**The 10 Approaches Tested & Rejected:**
1. **EMA trend-following:** Produced coin-flip accuracy.
2. **MTF (Multi-Timeframe) confluence:** Filtering 1H signals with 4H trends did not resolve whipsaws.
3. **ADX/Chop regime-filter:** Failed due to ADX inverting in different regimes (high in chop, fatal in bull).
4. **ATR-fixed TP/SL:** Did not universally protect against out-of-sample volatility.
5. **ADX regime-gate:** Attempted to block trades dynamically but failed to differentiate true trends from whipsaw spikes.
6. **Donchian breakout single-coin:** Appeared highly profitable on BTC, but proved to be heavily overfitted to a single asset's path.
7. **Trailing-ATR 2.0 and 3.5:** Tighter and wider trailing stops were both systematically hit during normal market noise.
8. **BBW-squeeze:** Single-parameter thresholds blocked genuine breakouts and failed in out-of-sample windows.
9. **Donchian multi-coin portfolio (Fixed and ATR-based SL/TP):** Aggregating BTC, ETH, BNB, and SOL proved the strategy fails across the broader market. ATR scaling explicitly worsened losses during volatile bull regimes.
10. **RSI/Bollinger mean-reversion:** Yielded exactly ~46-50% win rates on a 1:1 Risk/Reward setup, guaranteeing a net loss after fees.

**Explicit Conclusion:** Simple technical-rule-based entry engines on the 1H timeframe do not show a statistical edge in the 2023-2024 period tested. This is a rigorously evidence-based conclusion, not an engineering failure.

---

## Phase 2: Timeframe Expansion & Multi-Year Evaluation
**Status:** Completed & Rejected (Hypothesis Invalidated)

### The Hypothesis
Following Phase 1, we hypothesized that the 1H timeframe contains too much noise, and expanding to the 4H timeframe would filter out intraday whipsaws to reveal a genuine trend-following edge.

### Rigorous Evaluation (2020-2024 Macro Data)
To ensure our findings were not merely artifacts of the limited 2023-2024 dataset, we fetched 4.5 years of continuous BTC data (Jan 2020 to Aug 2024) spanning roughly 40,000 candles. This massive dataset was explicitly divided into 5 distinct macro-regimes to prevent "average masking":
1. 2020 (COVID Crash & Early Bull)
2. 2021 (Massive Bull Run)
3. 2022 (Brutal Bear & FTX Crash)
4. 2023 (Chop & Recovery)
5. 2024 (ETF Bull Run)

We tested our most promising baseline (Donchian-20 Breakout with ATR-scaled exits) on both 1H and 4H timeframes across all 5 regimes, enforcing the strict `95% CI Lower Bound >= 0.95` rule.

### Final Verdict: "Timeframe Expansion" Rejected
* **1H Timeframe:** Failed in 5 out of 5 macro regimes. Win rates hovered around 28-34%, completely mathematically destroying any edge over the 4.5 year span.
* **4H Timeframe:** Failed in 5 out of 5 macro regimes. While raw Profit Factors occasionally spiked due to small sample sizes (N ~ 40-80), the 95% Confidence Intervals revealed massive variance. The lower bound consistently crashed below the 0.95 threshold (hitting 0.46 - 0.80).

**Conclusion:** The failure of simple indicators is a genuine, consistent, multi-year mathematical reality of the crypto markets. It is not a small-sample anomaly. Expanding to a higher timeframe (4H) reduces trade frequency but proportionally inflates the size of whipsaw losses, ultimately providing zero statistical improvement to the edge.

---

## Phase 3: Future Directions (On Hold)
To proceed further in algorithmic trading, a fundamental pivot is required away from simple technical indicators. Potential avenues:
1. **Fundamentally different data sources:** Order-flow imbalances, volume profile, or fundamental sentiment analysis.
2. **Machine Learning / Feature-Learning:** Deep learning to discover complex, non-linear market patterns rather than hard-coded human rules.
