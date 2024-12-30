from .log import Log
from .broker import Broker
import math
from .DataManager import DataManager
from alpaca.trading import OrderType, OrderSide


class Strategies:
    def __init__(self):
        """
        Initialize the base Strategies class.
        """
        self.state = {}

    def execute(self, ticker: str, timeframe: str, broker: Broker, data, data_manager: DataManager):
        """
        Execute the strategy.
        --------------------------------------------------
        Parameters:
        -----------
        ticker : str
            The ticker symbol.
        timeframe : str
            The timeframe for execution.
        broker : Broker
            The broker to use for trading.
        data : list
            The historical data.
        data_manager : DataManager
            The data manager instance.
        --------------------------------------------------
        """
        raise NotImplementedError("Must implement execute method")


class Example(Strategies):
    def __init__(self):
        """
        Initialize the Example strategy.
        """
        super().__init__()
        self.state = {
            'example': None,
            'positions': 0,
            'bought_at': None,
        }

    def execute(self, ticker, timeframe, broker, data, data_manager):
        """
        Execute the Example strategy.
        --------------------------------------------------
        Parameters:
        -----------
        ticker : str
            The ticker symbol.
        timeframe : str
            The timeframe for execution.
        broker : Broker
            The broker to use for trading.
        data : list
            The historical data.
        data_manager : DataManager
            The data manager instance.
        --------------------------------------------------
        """
        if not broker.is_market_open():
            Log.auto(f'Market is closed. Skipping execution for {ticker} in {timeframe}')
            return
        Log.auto(f'Executing Example strategy for {ticker} in {timeframe} with data: {data}')


class QQQ(Strategies):
    def __init__(self):
        """
        Initialize the QQQ strategy.
        """
        super().__init__()
        self.state = {
            'position': 0,
            'stoploss': None,
            'capE': 0
        }

    def execute(self, ticker, timeframe, broker, data, data_manager):
        """
        Execute the QQQ strategy.
        --------------------------------------------------
        Parameters:
        -----------
        ticker : str
            The ticker symbol.
        timeframe : str
            The timeframe for execution.
        broker : Broker
            The broker to use for trading.
        data : list
            The historical data.
        data_manager : DataManager
            The data manager instance.
        --------------------------------------------------
        """
        if not broker.is_market_open():
            Log.auto(f'QQQ - Market is closed. Skipping execution for {ticker} in {timeframe}')
            return
        try:
            self.state['position'] = broker.get_positions(ticker)
            sto = (data[-1]['close'] - data[-1]['low']) / (data[-1]['high'] - data[-1]['low']) * 100
            
            if self.state['position'] == 0 and sto > 10:
                self.state['capE'] = math.floor(broker.get_cash() / data[-1]['close'])
                broker.place_order_sl(ticker, self.state['capE'], 'buy', stop_loss=broker.get_cash() / self.state['capE'], id='QQQ')
            elif self.state['position'] > 0 and data[-1]['close'] > data[-2]['high']:
                broker.place_order(asset=ticker, quantity=self.state['position'], side=OrderSide.SELL, id='QQQ')
        except Exception as e:
            Log.auto(f'Error in QQQ strategy: {e}')


class Test(Strategies):
    def __init__(self):
        """
        Initialize the Test strategy.
        """
        super().__init__()
         
    def execute(self, ticker: str, timeframe: str, broker: Broker, data, data_manager):
        """
        Execute the Test strategy.
        --------------------------------------------------
        Parameters:
        -----------
        ticker : str
            The ticker symbol.
        timeframe : str
            The timeframe for execution.
        broker : Broker
            The broker to use for trading.
        data : list
            The historical data.
        data_manager : DataManager
            The data manager instance.
        --------------------------------------------------
    """ 
    
        if broker.is_market_open():
            broker.place_order(ticker,1,'buy')