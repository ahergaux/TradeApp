import threading
from datetime import datetime, timedelta
import time
import pandas as pd
from .log import Log
from .strategies import Strategies,QQQ
from .DataManager import DataManager
from .broker import Broker

class StrategyThread(threading.Thread):
    def __init__(self, strategy, tickers, timeframe, broker: Broker, data_manager: DataManager):
        """
        Initialize the StrategyThread with strategy, tickers, timeframe, broker, and data manager.
        --------------------------------------------------
        Parameters:
        -----------
        strategy : Strategies
            The trading strategy to execute.
        tickers : list of str
            List of ticker symbols.
        timeframe : str
            Timeframe for strategy execution.
        broker : Broker
            The broker to use for trading.
        data_manager : DataManager
            The data manager instance.
        --------------------------------------------------
        """
        super().__init__()
        self.strategy = strategy()
        self.tickers = tickers
        self.timeframe = timeframe
        self.broker = broker
        self.data_manager = data_manager
        self.active = True

    def run(self):
        """
        Run the strategy thread. This function will repeatedly execute the strategy at specified intervals.
        """
        Log.auto(f'Strategy {self.strategy} thread start')
        try:
            time.sleep(self.get_sleep_seconds())
        except Exception as e:
            Log.auto(f'Error in initial sleep: {e}')
        while self.active:
            try:
                if self.broker.is_market_open():
                    for ticker in self.tickers:
                        data = self.data_manager.data[ticker][self.timeframe]
                        Log.auto(f'Strategy {self.strategy} launch for {ticker}')
                        try:
                            self.strategy.execute(ticker, self.timeframe, self.broker, data, self.data_manager)
                        except Exception as e:
                            Log.auto(f'{self.strategy} failed to run, error: {e}')
                sleep_duration = self.get_sleep_seconds()
                time.sleep(sleep_duration)
                Log.auto(f'Strategy {self.strategy} sleep for {sleep_duration}')
            except Exception as e:
                Log.auto(f'Error in strategy thread loop: {e}')

    def stop(self):
        """
        Stop the strategy thread.
        """
        self.active = False
        Log.auto(f'Strategy {self.strategy} thread stop')

    def get_sleep_seconds(self) -> int:
        """
        Calculate the number of seconds to sleep before the next execution based on the timeframe.
        --------------------------------------------------
        Returns:
        --------
        int
            Number of seconds to sleep.
        --------------------------------------------------
        """
        try:
            t = pd.Timestamp.now()
            if self.timeframe == 'M':
                return 60 - t.second + 4  # Run every minute + 4 sec
            elif self.timeframe == '5M':
                return 300 - t.second - t.minute % 5 * 60 + 4  # Run every 5 minutes + 4 sec
            elif self.timeframe == '15M':
                return 900 - t.second - t.minute % 15 * 60 + 4  # Run every 15 minutes + 4 sec
            elif self.timeframe == 'H':
                return 3600 - t.second - t.minute * 60 + 4  # Run every hour + 4 sec
            elif self.timeframe == 'D':
                target_time = t.replace(hour=15, minute=31, second=0, microsecond=0)  # Run every day at 15h31m00s
                if t > target_time:
                    target_time += timedelta(days=1)
                return int((target_time - t).total_seconds())
            return 100000
        except Exception as e:
            Log.auto(f'Error in get_sleep_seconds: {e}')
            return 60  # Default sleep time in case of error
