import re

with open("PROJECT_SUMMARY.md", "r") as f:
    content = f.read()

# Add Phase 3 details
phase3_content = """### Phase 3: Non-Predictive Approach (Grid Trading)
To explore alternatives to directional prediction, we engineered a mathematically sound Grid-Trading (Market-Making) bot. Instead of predicting price action, it attempted to farm market volatility within a dynamic 90-day High/Low rolling range with 1.5% fixed grid spacing and a 5% hard stop-loss to prevent bag-holding.

**Phase 3 Verdict:** Grid-Trading hypothesis explicitly rejected. The multi-window historical backtest proved that Grid-Trading merely converts directional-risk into massive tail-risk. While it generated a small profit (+2.67%) during choppy conditions, it severely underperformed during bull trends (sitting in USDT while the market soared) and suffered a catastrophic stop-loss hit (-14.41% single-window loss) during a flash crash (July 5th, 2024).

---

"""

content = content.replace("---", "---\n\n" + phase3_content, 1)

# Ensure the insertion point is correct by doing a more targeted replace:
# Let's just rewrite the whole file cleanly using the python script to guarantee format.
