# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
import logging
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import ta

logger = logging.getLogger(__name__)

class DonchianStrategy(IStrategy):
    """
    Donchian Breakout Strategy
    Based on 20-period High/Low breakout.
    Fixed TP 5%, SL 2%.
    """
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = '1h'

    # Can this strategy go short?
    can_short = True

    # Minimal ROI (5% target)
    minimal_roi = {
        "0": 0.05
    }

    # Stoploss (2%)
    stoploss = -0.02
    
    # Trailing stop: False (We want fixed TP/SL)
    trailing_stop = False

    # Process only new candles
    process_only_new_candles = True

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count = 20

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate Donchian Channels (20 period max high and min low)
        # We use shift(1) to avoid lookahead bias, meaning breakout is based on previous 20 candles
        dataframe['dh_20'] = dataframe['high'].rolling(20).max().shift(1)
        dataframe['dl_20'] = dataframe['low'].rolling(20).min().shift(1)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['dh_20']) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        dataframe.loc[
            (
                (dataframe['close'] < dataframe['dl_20']) &
                (dataframe['volume'] > 0)
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exits are purely handled by ROI and Stoploss
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        return dataframe
