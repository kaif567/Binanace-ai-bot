import pandas as pd
import pytest
from indicators.mtf import get_4h_trend_from_df, check_mtf_confluence, get_htf_trend_at_time


def _make_htf_candles(n=50, trend="BULLISH"):
    # base_time = 100 hours ago
    import time
    base_time = int(time.time() * 1000) - (n * 4 * 3600 * 1000)
    
    data = {
        "time": [base_time + i * 4 * 3600_000 for i in range(n)],
        "close": [50000.0 + i * 10 for i in range(n)]
    }
    df = pd.DataFrame(data)
    
    if trend == "BULLISH":
        df['ema20'] = [50000 + i * 10 for i in range(n)]
        df['ema50'] = [49000 + i * 5 for i in range(n)]
    elif trend == "BEARISH":
        df['ema20'] = [49000 + i * 5 for i in range(n)]
        df['ema50'] = [50000 + i * 10 for i in range(n)]
    elif trend == "SIDEWAYS":
        df['ema20'] = [50000.0] * n
        df['ema50'] = [50000.0] * n
        
    return df


def test_get_4h_trend_bullish():
    df = _make_htf_candles(trend="BULLISH")
    assert get_4h_trend_from_df(df) == "BULLISH"

def test_get_4h_trend_bearish():
    df = _make_htf_candles(trend="BEARISH")
    assert get_4h_trend_from_df(df) == "BEARISH"

def test_get_4h_trend_sideways():
    df = _make_htf_candles(trend="SIDEWAYS")
    assert get_4h_trend_from_df(df) == "SIDEWAYS"

def test_get_4h_trend_empty():
    assert get_4h_trend_from_df(pd.DataFrame()) == "SIDEWAYS"
    assert get_4h_trend_from_df(None) == "SIDEWAYS"

def test_check_mtf_confluence():
    assert check_mtf_confluence("UP", "BULLISH") == "ALIGNED"
    assert check_mtf_confluence("DOWN", "BEARISH") == "ALIGNED"
    assert check_mtf_confluence("UP", "BEARISH") == "CONFLICT"
    assert check_mtf_confluence("DOWN", "BULLISH") == "CONFLICT"
    
    # Sideways HTF allows trades (graceful degradation)
    assert check_mtf_confluence("UP", "SIDEWAYS") == "ALIGNED"
    assert check_mtf_confluence("DOWN", "SIDEWAYS") == "ALIGNED"
    
    # Neutral signals
    assert check_mtf_confluence("FLAT", "BULLISH") == "NEUTRAL"
    assert check_mtf_confluence("UNKNOWN", "BEARISH") == "NEUTRAL"

def test_get_htf_trend_at_time():
    # Construct an HTF dataframe with 2 candles
    # Candle 1: time=0 (closes at 14400000 - 1)
    # Candle 2: time=14400000 (closes at 28800000 - 1)
    data = {
        "time": [0, 14400000],
        "close": [50000.0, 51000.0],
        "ema20": [50000.0, 51000.0],
        "ema50": [49000.0, 49000.0]  # Always BULLISH if seen
    }
    df = pd.DataFrame(data)
    
    # 1h signal candle at time=0 (closes at 3600000 - 1)
    # At this time, HTF candle 1 hasn't closed yet!
    # So closed_htf should be empty -> SIDEWAYS
    assert get_htf_trend_at_time(df, 0) == "SIDEWAYS"
    
    # 1h signal candle at time=10800000 (closes at 14400000 - 1)
    # HTF candle 1 closes at the exact same ms (14400000 - 1)
    assert get_htf_trend_at_time(df, 10800000) == "BULLISH"
    
    # 1h signal candle at time=14400000 (closes at 18000000 - 1)
    # HTF candle 1 is closed, HTF candle 2 is not.
    # So trend from HTF candle 1 is used -> BULLISH
    assert get_htf_trend_at_time(df, 14400000) == "BULLISH"
