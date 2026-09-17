import pandas as pd

def get_4h_trend_from_df(df_4h):
    """
    Computes EMA20 and EMA50 on closed 4h candles if not already present.
    Returns the trend on the LAST closed candle.
    
    Returns: "BULLISH" | "BEARISH" | "SIDEWAYS"
    BULLISH  → EMA20_4h > EMA50_4h
    BEARISH  → EMA20_4h < EMA50_4h
    SIDEWAYS → insufficient data or exact match
    """
    if df_4h is None or len(df_4h) == 0:
        return "SIDEWAYS"
        
    df = df_4h.copy()
    
    # Calculate EMAs if missing
    if 'ema20' not in df.columns:
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    if 'ema50' not in df.columns:
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
    # We only care about the last closed candle
    last_row = df.iloc[-1]
    
    ema20 = last_row.get('ema20')
    ema50 = last_row.get('ema50')
    
    if pd.isna(ema20) or pd.isna(ema50):
        return "SIDEWAYS"
        
    if ema20 > ema50:
        return "BULLISH"
    elif ema20 < ema50:
        return "BEARISH"
    else:
        return "SIDEWAYS"


def check_mtf_confluence(signal_direction, htf_trend):
    """
    Checks if the 1h signal aligns with the 4h trend.
    
    Returns: "ALIGNED" | "CONFLICT" | "NEUTRAL"
    """
    if signal_direction == "FLAT" or signal_direction not in ("UP", "DOWN"):
        return "NEUTRAL"
        
    if htf_trend == "SIDEWAYS":
        # If HTF is sideways/unknown, we can't confirm or deny. 
        # Typically, a neutral HTF implies we might want to be cautious, 
        # but to avoid silent blocks on data gaps, we consider it ALIGNED.
        return "ALIGNED"
        
    if signal_direction == "UP" and htf_trend == "BULLISH":
        return "ALIGNED"
        
    if signal_direction == "DOWN" and htf_trend == "BEARISH":
        return "ALIGNED"
        
    return "CONFLICT"


def get_htf_trend_at_time(df_htf, signal_time_ms):
    """
    Given a 1h signal candle time, finds the correct HTF trend.
    Causal guarantee: Only uses HTF candles whose close_time <= 1h signal_time.
    
    signal_time_ms: typically the open time of the 1h candle.
    In Binance, a 1h candle opening at 10:00 closes at 10:59:59.999.
    
    We need the latest HTF candle that has ALREADY CLOSED by the time
    the 1h signal is generated.
    """
    if df_htf is None or len(df_htf) == 0:
        return "SIDEWAYS"
        
    # We assume df_htf has a 'time' column (open time) and standard intervals.
    # In live/backtest, 'time' is usually open time.
    # A 4h candle takes 4 hours (14400000 ms) to close.
    # So close_time = time + 14400000 - 1
    
    df = df_htf.copy()
    if 'close_time' not in df.columns:
        # Assuming 4h interval = 14,400,000 ms
        df['close_time'] = df['time'] + 14400000 - 1
        
    # Filter for HTF candles that have completely closed before or at the signal time.
    # Wait, the engine generates the signal on the CLOSED 1h candle. 
    # T = the 1h candle's open time. It closes at T + 3,600,000 - 1.
    # The signal is generated right after T + 3,600,000.
    # So we want HTF candles that closed <= T + 3600000.
    
    signal_close_time = signal_time_ms + 3600000 - 1
    
    closed_htf = df[df['close_time'] <= signal_close_time]
    
    if len(closed_htf) == 0:
        return "SIDEWAYS"
        
    return get_4h_trend_from_df(closed_htf)

