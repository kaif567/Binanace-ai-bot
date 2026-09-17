import math


# ─────────────────────────────────────────────────────────────────────────────
# Regime classifier — pure function, no I/O, no side-effects.
#
# All thresholds are passed as explicit parameters so that:
#   1. The threshold_sweep script can call this with many candidates without
#      touching this file.
#   2. The backtest engine passes the same thresholds it found via sweep,
#      ensuring backtest ↔ live consistency.
#   3. Unit tests can force any regime by controlling the inputs.
#
# Returns one of four strings:
#   "TRENDING"        — ADX is strong enough to indicate a directional trend.
#   "RANGING"         — ADX is weak; market is chopping/sideways. Block trades.
#   "HIGH_VOLATILITY" — ATR has surged sharply; spike/news condition. Block.
#   "UNKNOWN"         — Insufficient data (NaN indicators). Pass through
#                       gracefully so a data gap never silently blocks trades.
# ─────────────────────────────────────────────────────────────────────────────


def _is_finite(value):
    """Return True iff value can be cast to a finite float."""
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def classify_regime(
    df,
    adx_trending_thresh,
    adx_ranging_thresh,
    atr_lookback,
    atr_change_thresh,
):
    """
    Classify the current market regime from the last row of an
    indicator-enriched 1h DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: ``adx``, ``atr``.
        These are already produced by ``indicators.technical.add_indicators()``.
        The function reads only the **last** row (index -1) and the row at
        index -(atr_lookback + 1) for the ATR comparison.
    adx_trending_thresh : float
        ADX strictly above this → TRENDING.
        (Derived from threshold_sweep, not hard-coded.)
    adx_ranging_thresh : float
        ADX strictly below this → RANGING.
        Must be ≤ adx_trending_thresh.
    atr_lookback : int
        How many candles back to compare ATR for the surge calculation.
        E.g. 24 = compare current ATR against ATR 24 hours ago.
    atr_change_thresh : float
        Fractional ATR increase that triggers HIGH_VOLATILITY.
        E.g. 0.30 = 30% week-over-week surge.

    Returns
    -------
    str
        One of: "TRENDING", "RANGING", "HIGH_VOLATILITY", "UNKNOWN".

    Notes
    -----
    * RANGING and HIGH_VOLATILITY both block trades.
    * UNKNOWN passes through so a data gap never causes a silent block.
    * ADX priority: HIGH_VOLATILITY is checked first; ADX check follows.
      This means a market that is both volatile AND trending still gets
      classified as HIGH_VOLATILITY (more conservative).
    """

    if df is None or len(df) == 0:
        return "UNKNOWN"

    if "adx" not in df.columns or "atr" not in df.columns:
        return "UNKNOWN"

    last = df.iloc[-1]

    # ── ATR high-volatility check ─────────────────────────────────────────
    #
    # atr_change_pct = (atr_now - atr_N_candles_ago) / atr_N_candles_ago
    #
    # We need at least (atr_lookback + 1) rows to make a valid comparison.
    # If we don't have enough history, skip this check (conservative: don't
    # block on missing data).

    atr_now = last.get("atr")

    if _is_finite(atr_now) and int(atr_lookback) > 0:
        required_len = int(atr_lookback) + 1

        if len(df) >= required_len:
            atr_past_row = df.iloc[-(required_len)]
            atr_past = atr_past_row.get("atr")

            if _is_finite(atr_past) and float(atr_past) > 0:
                atr_change_pct = (
                    float(atr_now) - float(atr_past)
                ) / float(atr_past)

                if atr_change_pct > float(atr_change_thresh):
                    return "HIGH_VOLATILITY"

    # ── ADX trend-strength check ──────────────────────────────────────────

    adx = last.get("adx")

    if not _is_finite(adx):
        return "UNKNOWN"

    adx = float(adx)

    if adx > float(adx_trending_thresh):
        return "TRENDING"

    if adx < float(adx_ranging_thresh):
        return "RANGING"

    # ADX is in the "grey zone" between ranging and trending thresholds.
    # This is an ambiguous regime — treat conservatively as RANGING so
    # we don't enter in borderline conditions.
    return "RANGING"

