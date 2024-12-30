from enum import Enum



class FilesApp(Enum):
    Brokers = 'brokers.csv'
    Auto = 'automations.csv'
    Tickers = 'tickers.csv'

def timeframe_map ():
    from alpaca.data import TimeFrame

    return  {
    'M' : TimeFrame.Minute,
    'H' : TimeFrame.Hour,
    'D' : TimeFrame.Day,
    'W' : TimeFrame.Week
    }

def conversion_mexc_map ():
    return {
        'M': 'Min1',
        '5M' : 'Min5',
        '15M' : 'Min15',
        '1H' : 'Min60',
        'D' : 'Day1',
        'W' :'Week1',
    }

def conversion_map ():
    return {
        'M': 1,
        '5M' : 5,
        '15M' : 15,
        '1H' : 60,
        'D' : 1440,
        'W' :10080,
    }

def broker_map ():
    from .broker import Alpaca,Kraken,MEXCFutures,KrakenFutures
    return {
    'Alpaca' : Alpaca,
    'Kraken' : Kraken,
    'KrakenFutures' : KrakenFutures,
    'MEXCFutures' : MEXCFutures,
}

def strategy_map():
    from .strategies import QQQ,Test
    return {
        'QQQ': QQQ,
        'Test': Test
    }

def get_strategy_key(strategy_class):
    for key, value in strategy_map.items():
        if value == strategy_class:
            return key
    return None