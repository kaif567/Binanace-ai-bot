"""
Unit test for explicit signal override path in engine.py

Tests that when a dataframe contains an explicit
"signal" column with "STRONG BUY" or "STRONG SELL",
the backtest engine uses that signal directly without
calling calculate_market_score().
"""

import pandas as pd
from backtest.engine import run_advanced_backtest


def test_explicit_signal_override():
    """
    Test that explicit candle signals bypass scoring logic.
    """

    print("\n" + "="*50)
    print("TEST: Explicit Signal Override")
    print("="*50)

    # Create minimal test dataframe with explicit signals
    data = {
        "time": [
            1000000000000,
            1000003600000,
            1000007200000,
            1000010800000,
            1000014400000,
        ],
        "open": [100.0, 101.0, 102.0, 103.0, 104.0],
        "high": [101.0, 102.0, 103.0, 105.0, 106.0],
        "low": [99.0, 100.0, 101.0, 102.0, 103.0],
        "close": [100.5, 101.5, 102.5, 104.0, 105.0],
        "volume": [1000, 1000, 1000, 1000, 1000],
        # Explicit signals on closed candles
        "signal": [
            None,
            "STRONG BUY",   # Should trigger LONG entry
            None,
            "STRONG SELL",  # Should trigger SHORT entry
            None,
        ]
    }

    df = pd.DataFrame(data)

    # No strategy needed — explicit signals should work
    strategy = {
        "ema_fast": 10,
        "ema_slow": 50,
        "sl": 0.02,
        "tp": 0.05
    }

    result = run_advanced_backtest(
        df,
        initial_balance=1000,
        trade_amount=100,
        stop_loss=0.02,
        take_profit=0.05,
        fee=0.001,
        strategy=strategy,
        trade_start_index=1,
        force_close_at_end=True
    )

    # Verify results
    print("\n--- BACKTEST RESULT ---")
    print(f"Initial Balance: ${result['initial']}")
    print(f"Final Balance: ${result['final']}")
    print(f"Profit: ${result['profit']}")
    print(f"Trades: {result['trades']}")
    print(f"Wins: {result['wins']}")
    print(f"Losses: {result['losses']}")
    print(f"Win Rate: {result['win_rate']}%")

    print("\n--- TRADE HISTORY ---")
    for i, trade in enumerate(result['history']):
        print(f"\nTrade {i+1}:")
        print(f"  Type: {trade.get('type')}")
        print(f"  Position: {trade.get('position', 'N/A')}")
        print(f"  Price: {trade.get('price')}")
        print(f"  Signal: {trade.get('signal', 'N/A')}")
        print(f"  Reasons: {trade.get('reasons', 'N/A')}")
        print(f"  Exit Reason: {trade.get('exit_reason', 'N/A')}")

    # Assertions
    assert result['trades'] > 0, "No trades executed — explicit signals not triggered"

    # Check that at least one trade has explicit signal metadata
    entry_trades = [
        t for t in result['history']
        if t.get('type') in ['BUY', 'SHORT']
    ]

    assert len(entry_trades) > 0, "No entry trades found"

    # Verify explicit signal traces
    explicit_entries = [
        t for t in entry_trades
        if t.get('signal') in ['STRONG BUY', 'STRONG SELL']
    ]

    assert len(explicit_entries) > 0, \
        "No explicit signals found in entry trades — override path not working"

    # Verify reason contains "Explicit candle signal"
    for trade in explicit_entries:
        reasons = trade.get('reasons', [])
        assert 'Explicit candle signal' in reasons, \
            f"Entry trade missing explicit signal reason: {reasons}"

    print("\n" + "="*50)
    print("✅ TEST PASSED")
    print("="*50)
    print("\nExplicit signal override path is working correctly:")
    print(f"  - {len(explicit_entries)} explicit signal entries detected")
    print(f"  - Total trades executed: {result['trades']}")
    print(f"  - All explicit entries have correct reason metadata")

    return result


if __name__ == "__main__":
    test_explicit_signal_override()
