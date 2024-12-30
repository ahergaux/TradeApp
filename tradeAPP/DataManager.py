from collections import defaultdict, deque
import pandas as pd
import os
import time
import asyncio
import threading
from .log import Log

class DataManager:
    def __init__(self, broker, stocks: bool, tickers: list[str]):
        """
        Initialize the DataManager with broker, stocks, and tickers.
        --------------------------------------------------
        Parameters:
        -----------
        broker : Broker object
            The broker used for data connections.
        stocks : bool
            Flag to determine if stocks are being managed.
        tickers : list of str
            List of tickers to manage.
        --------------------------------------------------
        """
        self.lock = threading.Lock()
        self.tickers: list[str] = tickers
        self.stocks: bool = stocks
        self.broker = broker
        self.new_bar: dict = {}
        self.data = defaultdict(lambda: {
            'M': deque(maxlen=10080),
            '5M': deque(maxlen=8928),
            '15M': deque(maxlen=5952),
            'H': deque(maxlen=1488),
            'D': deque(maxlen=365)
        })

        self.init_data()

        self.requestThread = threading.Thread(target=self.broker.connect_ws, args=(self, self.tickers, self.stocks))
        self.requestThread.start()

        self.timeframeThread = threading.Thread(target=self.transform_data)
        self.timeframeThread.start()

    def init_data(self):
        """
        Fetch initial historical data from the broker and transform it.
        """
        datainit = self.broker.bars_from_today_to(self.tickers, self.stocks, 'M', day_back=1)
        transformed_data = self.transform_historical_data(datainit)
        with self.lock:
            for ticker in transformed_data:
                self.data[ticker]['M'].extend(transformed_data[ticker])
                df = pd.DataFrame(transformed_data[ticker])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                self.data[ticker]['5M'] = deque(
                    df.resample('5min', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=8928)
                self.data[ticker]['15M'] = deque(
                    df.resample('15min', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=5952)
                self.data[ticker]['H'] = deque(
                    df.resample('1h', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=1488)
                self.data[ticker]['D'] = deque(
                    df.resample('1D', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=365)
        self.archive_all_data()
        time.sleep(60-pd.Timestamp.now().second)

    def transform_historical_data(self, data):
        """
        Transform historical data to the standardized format.
        --------------------------------------------------
        Parameters:
        -----------
        data : dict
            Historical data received from the broker.
        --------------------------------------------------
        Returns:
        --------
        dict
            Transformed historical data.
        --------------------------------------------------
        """
        transformed_data = defaultdict(list)
        for bar in data:
            transformed_data[bar['symbol']].append({
                'open': bar['open'],
                'high': bar['high'],
                'low': bar['low'],
                'close': bar['close'],
                'volume': bar['volume'],
                'timestamp': bar['timestamp'],
                'symbol': bar['symbol']
            })
        return transformed_data

    def handle_ws_message(self, update_bar: dict):
        """
        Handle incoming websocket message and last data.
        --------------------------------------------------
        Parameters:
        -----------
        new_bar : dict
            New bar data received from the websocket.
        --------------------------------------------------
        """
        try:
            with self.lock:
                ticker = update_bar['symbol']
                Log.data(f"Handling new websocket message for {ticker}")
                self.new_bar[ticker]=update_bar
        except Exception as e:
            Log.data(f"Error in handle_ws_message: {e}")
        
    def aggregate_ohlc(self, group):
        """
        Aggregate OHLC data for a given group.
        --------------------------------------------------
        Parameters:
        -----------
        group : DataFrame
            Grouped data to aggregate.
        --------------------------------------------------
        Returns:
        --------
        Series
            Aggregated OHLC data.
        --------------------------------------------------
        """
        try:
            if len(group) > 1:
                return pd.Series({
                    'open': group['open'].iloc[0],
                    'high': group['high'].max(),
                    'low': group['low'].min(),
                    'close': group['close'].iloc[-1],
                    'volume': group['volume'].sum(),
                    'timestamp': group.index[-1],
                    'symbol': group['symbol'].iloc[0],
                })
            elif len(group) == 1:
                return pd.Series({
                    'open': group['open'].iloc[0],
                    'high': group['high'].iloc[0],
                    'low': group['low'].iloc[0],
                    'close': group['close'].iloc[0],
                    'volume': group['volume'].iloc[0],
                    'timestamp': group.index[-1],
                    'symbol': group['symbol'].iloc[0],
                })
            else:
                return pd.Series({
                    'open': None,
                    'high': None,
                    'low': None,
                    'close': None,
                    'volume': 0,
                    'timestamp': None,
                    'symbol': None,
                })
        except Exception as e:
            Log.data(f"Error in aggregate_ohlc: {e} for {group['symbol'].iloc[0]}")
            return pd.Series({
                'open': None,
                'high': None,
                'low': None,
                'close': None,
                'volume': 0,
                'timestamp': None,
                'symbol': None,
            })

    def count_tickers(self, timeframe):
        """
        Count the number of tickers with data in a specific timeframe.
        --------------------------------------------------
        Parameters:
        -----------
        timeframe : str
            The timeframe to count tickers for.
        --------------------------------------------------
        Returns:
        --------
        int
            Number of tickers with data in the specified timeframe.
        --------------------------------------------------
        """
        count = 0
        try:
            for ticker, timeframes in self.data.items():
                if len(timeframes[timeframe]) > 0:
                    count += 1
        except Exception as e:
            Log.data(f"Error in count_tickers: {e}")
        return count

    def count_new_bar(self) -> bool:
        """
        Count the number of tickers with data in a specific timeframe.
        --------------------------------------------------
        Parameters:
        -----------
        timeframe : str
            The timeframe to count tickers for.
        --------------------------------------------------
        Returns:
        --------
        int
            Number of tickers with data in the specified timeframe.
        --------------------------------------------------
        """
        try:    
            if len(self.new_bar) > 0:
                return True
        except Exception as e:
            Log.data(f"Error in count_tickers: {e}")
        return False

    def transform_data(self):
        """
        Transform data for different timeframes and archive it.
        This function runs in a separate thread.
        --------------------------------------------------
        """
        Log.data('Transform data thread has been launched')
        while not self.count_new_bar():
            Log.data('Waiting more data to transform')
            time.sleep(60 - pd.Timestamp.now().second)
        while True:
            with self.lock:
                Log.data('Transforming data..')
                try:
                    if self.broker.is_market_open():
                        for ticker in self.tickers: # type: ignore
                            # Check if new_bar data is available for the ticker
                            if ticker in self.new_bar and self.new_bar[ticker]:
                                self.data[ticker]['M'].append(self.new_bar[ticker])
                            else:
                                # If new_bar data is not available, use the last data point
                                if len(self.data[ticker]['M']) > 0:
                                    self.data[ticker]['M'].append(self.data[ticker]['M'][-1])
                            
                            if len(self.data[ticker]['M']) > 0:
                                self.archive_data(ticker, 'M')
                                df = pd.DataFrame(self.data[ticker]['M'])
                                df['timestamp'] = pd.to_datetime(df['timestamp'])
                                df.set_index('timestamp', inplace=True)
                                if pd.Timestamp.now().minute % 5 == 0:
                                    Log.data(f'Transforming 5M data for {ticker}')
                                    self.data[ticker]['5M'] = deque(
                                        df.resample('5min', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=8928)
                                    self.archive_data(ticker=ticker, timeframe='5M')
                                if pd.Timestamp.now().minute % 15 == 0:
                                    Log.data(f'Transforming 15M data for {ticker}')
                                    self.data[ticker]['15M'] = deque(
                                        df.resample('15min', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=5952)
                                    self.archive_data(ticker=ticker, timeframe='15M')
                                if pd.Timestamp.now().minute == 0:
                                    Log.data(f'Transforming H data for {ticker}')
                                    self.data[ticker]['H'] = deque(
                                        df.resample('1h', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=1488)
                                    self.archive_data(ticker=ticker, timeframe='H')
                                if pd.Timestamp.now().minute == 0 and pd.Timestamp.now().hour == 22:
                                    Log.data(f'Transforming D data for {ticker}')
                                    self.data[ticker]['D'] = deque(
                                        df.resample('1D', label='right').apply(self.aggregate_ohlc).to_dict('records'), maxlen=365)
                                    self.archive_data(ticker=ticker, timeframe='D')
                    Log.data('Transforming data end')
                except Exception as e:
                    Log.data(f'Error in transforming data: {e}')
            time.sleep(60 - pd.Timestamp.now().second)

    def print_data(self):
        """
        Print all the stored data.
        --------------------------------------------------
        """
        try:
            for ticker in self.tickers: # type: ignore
                print(f"Data for {ticker}:")
                for timeframe, data in self.data[ticker].items():
                    print(f"  {timeframe}: {list(data)}")
        except Exception as e:
            Log.data(f"Error in print_data: {e}")

    def get_data(self, ticker: str, timeframe: str):
        """
        Get data for a specific ticker and timeframe.
        --------------------------------------------------
        Parameters:
        -----------
        ticker : str
            The ticker to get data for.
        timeframe : str
            The timeframe to get data for.
        --------------------------------------------------
        Returns:
        --------
        list
            List of data for the specified ticker and timeframe.
        --------------------------------------------------
        """
        with self.lock:
            try:
                return list(self.data[ticker][timeframe])
            except Exception as e:
                Log.data(f"Error in get_data: {e}")
                return []

    def archive_data(self, ticker: str, timeframe: str):
        """
        Archive last bar data for a specific ticker and timeframe to a CSV file.
        --------------------------------------------------
        Parameters:
        -----------
        ticker : str
            The ticker to archive data for.
        timeframe : str
            The timeframe to archive data for.
        --------------------------------------------------
        """
        try:
            Log.data(f'Archiving {timeframe} data for {ticker}')
            file_path = f'data/{self.broker.broker_type}/{timeframe}/{ticker.replace("/", "")}.csv'
            file_exists = os.path.isfile(file_path)

            last_bar = self.data[ticker][timeframe][-1]
            df = pd.DataFrame([last_bar])

            with open(file_path, 'a') as f:
                df.to_csv(f, header=not file_exists, index=False)

            Log.data(f'Data saved for {ticker}')
        except Exception as e:
            Log.data(f'An exception occurred in archive_data: {e}')

    def archive_all_data(self):
        """
        Archive last bar data for all tickers and all timeframes to CSV files.
        """
        try:
            Log.data(f'Archiving all data from database')
            for ticker in self.tickers:  # type: ignore
                for timeframe in self.data[ticker]:
                    Log.data(f'Archiving data {timeframe} for {ticker}')
                    file_path = f'data/{self.broker.broker_type}/{timeframe}/{ticker.replace("/", "")}.csv'
                    file_exists = os.path.isfile(file_path)

                    data = self.data[ticker][timeframe]
                    df = pd.DataFrame(data)

                    with open(file_path, 'a') as f:
                        df.to_csv(f, header=not file_exists, index=False)
                    Log.data(f'Data {timeframe} saved for {ticker}')

        except Exception as e:
            Log.data(f'An exception occurred in archive_all_data: {e}')

    def stop(self):
        """
        Stop the DataManager and its threads.
        --------------------------------------------------
        """
        try:
            asyncio.get_event_loop().run_until_complete(self.broker.unsubscribe_all(self.tickers))
            self.requestThread.join()
            self.timeframeThread.join()
            Log.data(f'DataManager of {self.broker.broker_type} has been stopped and the subscription in the same time.')
        except Exception as e:
            Log.data(f'Error in stop: {e}')

    def actualize(self, tickers: list[str] | None , broker ):
        """
        Actualize the DataManager with new tickers or broker.
        --------------------------------------------------
        Parameters:
        -----------
        tickers : list of str or None
            The new list of tickers.
        broker : Broker object or None
            The new broker object.
        --------------------------------------------------
        """
        try:
            if tickers is None and broker is None:
                Log.data(f"Actualization of {self.broker.broker_type} DataManager went wrong. Tickers or broker are missing.")
                raise TypeError('tickers and broker can not be not None at the same time')
            
            with self.lock:
                Log.data(f'DataManager {self.broker.broker_type} stopped the subscription to actualize the tickers')
                asyncio.get_event_loop().run_until_complete(self.broker.unsubscribe_all(self.tickers))
                self.requestThread.join()
                if tickers is not None : 
                    self.tickers = tickers 
                if broker is not None:
                    self.broker = broker
                time.sleep(2)
                self.requestThread = threading.Thread(target=self.broker.connect_ws, args=(self, self.tickers, self.stocks))
                self.requestThread.start()
                Log.data(f'DataManager {self.broker.broker_type} restarted the subscription')
        
        except Exception as e:
            Log.data(f'Error in actualize: {e}')
