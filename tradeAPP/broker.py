import math
import pandas as pd
from alpaca.data import CryptoBarsRequest, CryptoHistoricalDataClient, StockLatestBarRequest, DataFeed, StockHistoricalDataClient, CryptoLatestBarRequest, StockBarsRequest, TimeFrame
from alpaca.trading import TradingClient, StopLimitOrderRequest, OrderType, TimeInForce, OrderSide, ClosePositionRequest
from alpaca.common import SupportedCurrencies
from .log import Log
import krakenex
import asyncio
import websockets
import requests
import json
import threading
from datetime import datetime, timedelta
from urllib.parse import urlencode
from .DataManager import DataManager
from .enums import timeframe_map,conversion_map,conversion_mexc_map

class Broker:
    """
    Classe Broker de base pour les connexions et opérations avec les brokers.
    -------------------------------------------------------------------------
    Methods:
    --------
    connect_ws(data_manager, tickers, stocks):
        Méthode pour se connecter au websocket du broker.

    get_actual_bar(assets, stocks):
        Méthode pour obtenir les dernières données de barres.

    bars_from_today_to(asset, stocks, timeframe, day_back=0, hour_back=0, minute_back=0):
        Méthode pour obtenir les barres historiques.

    get_account_info():
        Méthode pour obtenir les informations du compte.

    get_cash():
        Méthode pour obtenir les informations sur les liquidités.

    get_positions(asset):
        Méthode pour obtenir les positions ouvertes.

    place_order(asset, quantity, side, id='default'):
        Méthode pour passer une commande.

    place_order_sl(asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        Méthode pour passer une commande avec stop-loss et/ou take-profit.

    is_market_open():
        Méthode pour vérifier si le marché est ouvert.
    -------------------------------------------------------------------------
    """
    def __init__(self, name: str, api_key: str, api_secret: str, broker_type: str):
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.broker_type = broker_type

    def connect_ws(self, data_manager: DataManager, tickers: list[str], stocks: bool):
        """
        Méthode pour se connecter au websocket du broker.
        -------------------------------------------------
        Parameters:
        -----------
        data_manager : DataManager
            L'objet qui recevra les données.
        tickers : list[str]
            Liste des tickers à souscrire.
        stocks : bool
            Indique si les tickers sont des actions (True) ou des cryptos (False).
        -------------------------------------------------
        """
        raise NotImplementedError("Must implement connect_ws method")

    def unsubscribe_all(self, tickers : list[str]):
        raise NotImplementedError("Must implement unsubscribe_all method")

    def get_actual_bar(self, assets, stocks):
        raise NotImplementedError("Must implement get_actual_bar method")

    def bars_from_today_to(self, asset, stocks, timeframe, day_back=0, hour_back=0, minute_back=0):
        raise NotImplementedError("Must implement bars_from_today_to method")

    def get_account_info(self):
        raise NotImplementedError("Must implement get_account_info method")

    def get_cash(self):
        raise NotImplementedError("Must implement get_cash method")

    def get_positions(self, asset):
        raise NotImplementedError("Must implement get_positions method")

    def place_order(self, asset, quantity, side, id='default'):
        raise NotImplementedError("Must implement place_order method")

    def place_order_sl(self, asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        raise NotImplementedError("Must implement place_order_sl method")

    def is_market_open(self):
        raise NotImplementedError("Must implement is_market_open method")

class Alpaca(Broker):
    """
    Classe Alpaca pour les opérations avec le broker Alpaca.

     Alpaca est une plateforme d'échange Spot

    --------------------------------------------------------
    Methods:
    --------
    connect_ws(data_manager, tickers, stocks):
        Connexion au websocket d'Alpaca.

    start_event_loop():
        Démarre la boucle d'événements asynchrones.

    unsubscribe_all():
        Désabonne tous les tickers.

    subscribe_to_updates(tickers):
        Souscrit aux mises à jour des tickers.

    process_message(message):
        Traite les messages reçus du websocket.

    get_actual_bar(assets, stocks):
        Obtient les dernières barres de données.

    bars_from_today_to(asset, stocks, timeframe, day_back=0, hour_back=0, minute_back=0):
        Obtient les barres historiques des données.

    get_account_info():
        Obtient les informations du compte.

    get_cash():
        Obtient les informations sur les liquidités.

    get_positions(asset):
        Obtient les positions ouvertes.

    place_order(asset, quantity, side, id='default'):
        Passe une commande.

    place_order_sl(asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        Passe une commande avec stop-loss et/ou take-profit.

    is_market_open():
        Vérifie si le marché est ouvert.
    --------------------------------------------------------
    """
    def __init__(self, name: str, api_key: str, api_secret: str, broker_type: str):
        super().__init__(name, api_key, api_secret, broker_type)
        self.client_crypto = CryptoHistoricalDataClient()
        self.client_stock = StockHistoricalDataClient(self.api_key, self.api_secret)
        self.client_trading = TradingClient(self.api_key, self.api_secret)
        self.ws_url = None
        self.ws_task = None
        self.data_manager = None
        self.lock = threading.Lock()
        self.loop = None
        self.thread = None
        self.stocks : bool | None = None

    def connect_ws(self, data_manager, tickers, stocks):
        self.stocks=stocks
        self.data_manager = data_manager
        if stocks:
            self.ws_url = 'wss://stream.data.alpaca.markets/v2/iex'
        else:
            self.ws_url = 'wss://stream.data.alpaca.markets/v1beta3/crypto/us'
        self.start_event_loop()
        self.ws_task = asyncio.run_coroutine_threadsafe(self.subscribe_to_updates(tickers), self.loop)  # type: ignore

    def start_event_loop(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()

    def unsubscribe_all(self):
        try:
            with websockets.connect(self.ws_url) as websocket:  # type: ignore
                message = {
                    "action": "unsubscribe",
                    "bars": ["*"],
                }
                websocket.send(json.dumps(message))

                resp = websocket.recv()
                response = json.loads(resp)
                Log.request(f"Auth Response: {response}")
        except Exception as e:
            Log.request(f'Error for unsubscribe in Alpaca: {e}')

    async def subscribe_to_updates(self, tickers):
        Log.request('Subscription thread has been launched for Alpaca')
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:  # type: ignore
                    auth_message = {
                        "action": "auth",
                        "key": self.api_key,
                        "secret": self.api_secret
                    }
                    await websocket.send(json.dumps(auth_message))

                    response = await websocket.recv()
                    auth_response = json.loads(response)
                    Log.request(f"Auth Response: {auth_response}")

                    if isinstance(auth_response, dict) and auth_response.get('data', {}).get('status') != 'authorized':
                        Log.request("Authorization failed!")
                        return

                    listen_message = {
                        "action": "subscribe",
                        "bars": tickers
                    }
                    await websocket.send(json.dumps(listen_message))

                    while True:
                        response = await websocket.recv()
                        crypto_update = json.loads(response)
                        if isinstance(crypto_update, dict):
                            self.process_message(crypto_update)
                        elif isinstance(crypto_update, list):
                            for update in crypto_update:
                                self.process_message(update)

            except websockets.ConnectionClosedError as e:
                Log.request(f"Connection closed with error: {e}")
                Log.request("Attempting to reconnect to Alpaca in 5 seconds...")
                await asyncio.sleep(5)
            except json.JSONDecodeError as e:
                Log.request(f"Error decoding JSON: {e}")
            except Exception as e:
                Log.request(f"An unexpected error occurred in Broker/Alpaca, Error: {e}")
                break

    def process_message(self, message):
        try:
            if 'S' in message:
                ticker = message.get('S')
                new_bar = {
                    'open': message.get('o'),
                    'high': message.get('h'),
                    'low': message.get('l'),
                    'close': message.get('c'),
                    'volume': message.get('v'),
                    'timestamp': pd.Timestamp(message.get('t')),
                    'symbol': ticker,
                }
                with self.lock:
                    self.data_manager.handle_ws_message(new_bar)  # type: ignore
            else:
                Log.request(f"Unexpected message format: {message}")
        except KeyError as e:
            Log.request(f"Key error processing message: {e}")
        except Exception as e:
            Log.request(f"Error processing message: {e}")

    def get_actual_bar(self, assets, stocks):
        try:
            if stocks:
                request = StockLatestBarRequest(
                    symbol_or_symbols=assets,
                    feed=DataFeed.IEX,
                    currency=SupportedCurrencies.USD,
                )
                data = self.client_stock.get_stock_latest_bar(request)
            else:
                request = CryptoLatestBarRequest(
                    symbol_or_symbols=assets,
                )
                data = self.client_crypto.get_crypto_latest_bar(request)
            
            result = {key: {
                        'open': val.open,
                        'high': val.high,
                        'low': val.low,
                        'close': val.close,
                        'volume': val.volume,
                        'timestamp': val.timestamp
                    } for key, val in data.items()}
            return result

        except Exception as e:
            Log.request(f"Error fetching actual bar: {e}")
            return None

    def bars_from_today_to(self, assets, stocks, time, day_back=0, hour_back=0, minute_back=0):
        try:
            timeframe = timeframe_map()[time]
            start_time = pd.Timestamp(datetime.now() - timedelta(days=day_back, hours=hour_back+2, minutes=minute_back))
            end_time = pd.Timestamp(datetime.now())
            standardized_data = []
            request_params = {}
            for asset in assets:
                if stocks:
                    request_params = {
                        "symbol_or_symbols": asset,
                        "start": start_time,
                        "end": end_time,
                        "timeframe": timeframe,
                        "adjustment": None,
                        "currency": SupportedCurrencies.USD,
                        "feed": DataFeed.IEX
                    }
                    request = StockBarsRequest(**request_params)
                    data = self.client_stock.get_stock_bars(request)
                else:
                    request_params = {
                        "symbol_or_symbols": asset,
                        "start": start_time,
                        "end": end_time,
                        "timeframe": timeframe,
                    }
                    request = CryptoBarsRequest(**request_params)
                    data = self.client_crypto.get_crypto_bars(request)

                # Standardize the data
                for bar in data[asset]:
                    standardized_data.append({
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume,
                        'symbol': asset
                    })

            return standardized_data

        except Exception as e:
            Log.request(f"Error fetching bars: {e}")
            return []

    def get_account_info(self):
        try:
            account_info = self.client_trading.get_account()
            return {
                'cash': account_info.cash, # type: ignore
                'buying_power': account_info.buying_power, # type: ignore
                'equity': account_info.equity, # type: ignore
                'portfolio_value': account_info.portfolio_value, # type: ignore
            }
        except Exception as e:
            Log.request(f"Error fetching account info: {e}")
            return None

    def get_cash(self):
        try:
            account_info = self.client_trading.get_account()
            return account_info.cash # type: ignore
        except Exception as e:
            Log.request(f"Error fetching cash info: {e}")
            return None

    def get_positions(self, asset):
        try:
            positions = self.client_trading.get_all_positions()
            for position in positions:
                if position.symbol == asset: # type: ignore
                    return {
                        'symbol': position.symbol, # type: ignore
                        'qty': position.qty, # type: ignore
                        'avg_entry_price': position.avg_entry_price, # type: ignore
                        'market_value': position.market_value, # type: ignore
                        'cost_basis': position.cost_basis, # type: ignore
                        'unrealized_pl': position.unrealized_pl, # type: ignore
                        'unrealized_plpc': position.unrealized_plpc, # type: ignore
                        'current_price': position.current_price, # type: ignore
                    }
            return None
        except Exception as e:
            Log.request(f"Error fetching position: {e}")
            return None

    def place_order(self, asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        try:
            if take_profit and stop_loss is None:
                order = StopLimitOrderRequest(
                    symbol=asset,
                    qty=quantity,
                    side=OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL,
                    type=OrderType.STOP_LIMIT,
                    time_in_force=TimeInForce.GTC,
                    limit_price=take_profit,
                    stop_price=stop_loss,
                )
            else:
                order = StopLimitOrderRequest(
                    symbol=asset,
                    qty=quantity,
                    side=OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL,
                    type=OrderType.MARKET,
                    time_in_force=TimeInForce.GTC,
                )
            response = self.client_trading.submit_order(order)
            Log.order(f'{asset}->{side} for {quantity} ')
            return response
        except Exception as e:
            Log.request(f"Error placing order: {e}")
            return None

    def is_market_open(self):
        if not self.stocks:
            return True
        try:
            clock = self.client_trading.get_clock()
            return clock.is_open # type: ignore
        except Exception as e:
            Log.request(f"Error checking if market is open: {e}")
            return None

class Kraken(Broker):#HS
    """
    Classe Kraken pour les opérations avec le broker Kraken.

    Kraken est une plateforme d'échange Spot

    --------------------------------------------------------
    Methods:
    --------
    connect_ws(data_manager, tickers, stocks=True):
        Connexion au websocket de Kraken.

    start_event_loop():
        Démarre la boucle d'événements asynchrones.

    subscribe_to_updates(tickers):
        Souscrit aux mises à jour des tickers.

    stop():
        Arrête la souscription aux mises à jour des tickers.

    process_message(message):
        Traite les messages reçus du websocket.

    get_actual_bar(assets):
        Obtient les dernières barres de données.

    bars_from_today_to(asset, stocks, timeframe, day_back=0, hour_back=0, minute_back=0):
        Obtient les barres historiques des données.

    get_account_info():
        Obtient les informations du compte.

    get_cash():
        Obtient les informations sur les liquidités.

    get_positions(asset):
        Obtient les positions ouvertes.

    place_order(asset, quantity, side, id='default'):
        Passe une commande.

    place_order_sl(asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        Passe une commande avec stop-loss et/ou take-profit.

    is_market_open():
        Vérifie si le marché est ouvert.
    --------------------------------------------------------
    """
    def __init__(self, name: str, api_key: str, api_secret: str, broker_type: str):
        super().__init__(name, api_key, api_secret, broker_type)
        self.api = krakenex.API(key=api_key, secret=api_secret)
        self.ws_url = 'wss://ws.kraken.com/v2'
        self.ws_task = None
        self.data_manager = None
        self.lock = threading.Lock()
        self.loop = None
        self.thread = None
        self.stop_event = asyncio.Event()

    def connect_ws(self, data_manager: DataManager, tickers: list[str], stocks: bool = True):
        """
        Méthode pour se connecter au websocket du broker Kraken.
        --------------------------------------------------------
        Parameters:
        -----------
        data_manager : DataManager
            L'objet qui recevra les données.
        tickers : list[str]
            Liste des tickers à souscrire.
        stocks : bool
            Indique si les tickers sont des actions (True) ou des cryptos (False).
        --------------------------------------------------------
        """
        self.data_manager = data_manager
        self.start_event_loop()
        self.ws_task = asyncio.run_coroutine_threadsafe(self.subscribe_to_updates(tickers), self.loop)  # type: ignore

    def start_event_loop(self):
        """
        Méthode pour démarrer la boucle d'événements asynchrones.
        --------------------------------------------------------
        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()

    async def unsubscribe_all(self, tickers : list[str]):
        async with websockets.connect(self.ws_url) as websocket : 
            unsubscribe_message = {
                            "method": "unsubscribe",
                            "params": {
                                "channel": "ohlc",
                                "symbol": tickers,
                                "interval": 1
                            }
                        }
            await websocket.send(json.dumps(unsubscribe_message))

    async def subscribe_to_updates(self, tickers: list[str]):
        """
        Méthode pour souscrire aux mises à jour des tickers.
        ----------------------------------------------------
        Parameters:
        -----------
        tickers : list[str]
            Liste des tickers à souscrire.
        ----------------------------------------------------
        """
        Log.request('Subscription thread has been launched for Kraken')
        while not self.stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    subscribe_message = {
                        "method": "subscribe",
                        "params": {
                            "channel": "ohlc",
                            "snapshot": False,
                            "symbol": tickers
                        }
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    Log.request(f"Sent subscribe message: {subscribe_message}")

                    while not self.stop_event.is_set():
                        response = await websocket.recv()
                        message = json.loads(response)
                        if 'event' in message and message['event'] == 'subscriptionStatus':
                            Log.request(f"Subscription status: {message}")

                        self.process_message(message)

            except websockets.ConnectionClosedError as e:
                Log.request(f"Connection closed with error: {e}")
                Log.request("Attempting to reconnect in 5 seconds...")
                await asyncio.sleep(5)
            except json.JSONDecodeError as e:
                Log.request(f"Error decoding JSON: {e}")
            except Exception as e:
                Log.request(f"An unexpected error occurred: {e}")

    async def stop(self):
        """
        Méthode pour arrêter la souscription aux mises à jour des tickers.
        ------------------------------------------------------------------
        """
        self.stop_event.set()

    def process_message(self, message):
        """
        Méthode pour traiter les messages reçus du websocket.
        -----------------------------------------------------
        Parameters:
        -----------
        message : dict
            Message reçu du websocket.
        -----------------------------------------------------
        """
        try:
            if message['channel'] == 'ohlc':
                data = message['data'][0]
                ticker = data['symbol']
                new_bar = {
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'close': data['close'],
                    'volume': data['volume'],
                    'timestamp': pd.Timestamp(data['timestamp'], unit='s'),
                    'symbol': ticker,
                }

                with self.lock:
                    self.data_manager.handle_ws_message(new_bar)  # type: ignore
                            
            elif message['channel'] == 'heartbeat':
                pass
            else:
                Log.request(f"Unexpected message format: {message}")
        except KeyError as e:
            Log.request(f"Key error processing message: {e}")
        except Exception as e:
            Log.request(f"Error processing message: {e}")

    def get_actual_bar(self, assets: list[str]):
        """
        Méthode pour obtenir les dernières barres de données.
        -----------------------------------------------------
        Parameters:
        -----------
        assets : list[str]
            Liste des actifs à obtenir.
        -----------------------------------------------------
        """
        data = {}
        for asset in assets:
            try:
                response = self.api.query_public('OHLC', {'pair': asset, 'interval': 1})
                if 'error' in response and response['error']:
                    Log.request(f"Error fetching data for {asset}: {response['error']}")
                    continue
                ohlc_data = response['result'][asset]
                latest_bar = ohlc_data[-1]
                data[asset] = {
                    'open': float(latest_bar[1]),
                    'high': float(latest_bar[2]),
                    'low': float(latest_bar[3]),
                    'close': float(latest_bar[4]),
                    'volume': float(latest_bar[6]),
                    'timestamp': datetime.utcfromtimestamp(int(latest_bar[0])).isoformat(),
                    'symbol': asset,
                }
            except Exception as e:
                Log.request(f"Error fetching actual bar for {asset}: {e}")
        Log.request('Data from broker received')
        return data

    def bars_from_today_to(self, assets: list[str], stocks : bool, timeframe: str, day_back: int = 0, hour_back: int = 0, minute_back: int = 0):
        """
        Méthode pour obtenir les barres historiques des données.
        --------------------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à obtenir.
        timeframe : int
            Intervalle de temps pour les barres.
        day_back : int, optional
            Nombre de jours en arrière.
        hour_back : int, optional
            Nombre d'heures en arrière.
        minute_back : int, optional
            Nombre de minutes en arrière.
        --------------------------------------------------------
        """
        try:
            start_time = (datetime.now() - timedelta(days=day_back, hours=hour_back , minutes=minute_back)).timestamp()
            standardized_data = []

            for asset in assets:
                request = {
                    'pair': asset,
                    'interval': conversion_map()[timeframe],
                    'since': int(start_time)
                }
                response = self.api.query_public('OHLC', request)
                if 'error' in response and response['error']:
                    Log.request(f"Error fetching data for {asset}: {response['error']}")
                    continue

                data = response['result'][asset]
                
                # Standardize the data
                for bar in data:
                    standardized_data.append({
                        'timestamp': datetime.fromtimestamp(bar[0])-timedelta(hours=2),
                        'open': float(bar[1]),
                        'high': float(bar[2]),
                        'low': float(bar[3]),
                        'close': float(bar[4]),
                        'volume': float(bar[6]),
                        'symbol': asset
                    })

            return standardized_data

        except Exception as e:
            Log.request(f"Error fetching bars: {e}")
            return []

    def get_account_info(self):
        """
        Méthode pour obtenir les informations du compte.
        ------------------------------------------------
        """
        try:
            Log.request('Asking account info..')
            return self.api.query_private('Balance')
        except Exception as e:
            Log.request(f"Error fetching account info: {e}")
            return None

    def get_cash(self):
        """
        Méthode pour obtenir les informations sur les liquidités.
        ---------------------------------------------------------
        """
        try:
            Log.request('Asking cash info..')
            balance = self.get_account_info()
            return balance.get('ZUSD', 0.0)  # type: ignore # Assuming USD as base currency
        except Exception as e:
            Log.request(f"Error fetching cash info: {e}")
            return None

    def get_positions(self, asset: str):
        """
        Méthode pour obtenir les positions ouvertes.
        --------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à obtenir.
        --------------------------------------------
        """
        try:
            Log.request('Asking open positions..')
            balance = self.get_account_info()
            return balance.get(asset, 0.0) # type: ignore
        except Exception as e:
            Log.request(f"Error fetching positions: {e}")
            return None

    def place_order(self, asset: str, quantity: float, side: str, id: str = 'default'):
        """
        Méthode pour passer une commande.
        ---------------------------------
        Parameters:
        -----------
        asset : str
            Actif à acheter/vendre.
        quantity : float
            Quantité à acheter/vendre.
        side : str
            Type d'opération ('buy' ou 'sell').
        id : str, optional
            Identifiant de la commande.
        ---------------------------------
        """
        try:
            order = {
                'pair': asset,
                'type': side,
                'ordertype': 'market',
                'volume': quantity
            }
            Log.request(f'Order submit to the broker: {side} {quantity} {asset}')
            res = self.api.query_private('AddOrder', order)
            Log.request(f'Order answer for {side} {quantity} {asset} received: {res}')
            Log.order(f'{id} - {side} {quantity} {asset}')
            return res
        except Exception as e:
            Log.request(f"Error placing order: {e}")
            return None

    def place_order_sl(self, asset: str, quantity: float, side: str, take_profit: float | None = None, stop_loss: float | None = None, id: str = 'default'):
        """
        Méthode pour passer une commande avec stop-loss et/ou take-profit.
        ------------------------------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à acheter/vendre.
        quantity : float
            Quantité à acheter/vendre.
        side : str
            Type d'opération ('buy' ou 'sell').
        take_profit : float, optional
            Prix de prise de profit.
        stop_loss : float, optional
            Prix de stop-loss.
        id : str, optional
            Identifiant de la commande.
        ------------------------------------------------------------------
        """
        try:
            order = {
                'pair': asset,
                'type': side,
                'ordertype': 'stop-loss-limit' if stop_loss else 'take-profit-limit' if take_profit else 'market',
                'volume': quantity,
                'price': take_profit or stop_loss
            }
            Log.request(f'Send {id} - {side} {quantity} {asset}..')
            res = self.api.query_private('AddOrder', order)
            Log.request(f'{id} - {side} {quantity} {asset} received: {res}')
            Log.order(f'{id} - {side} {quantity} {asset}')
            return res
        except Exception as e:
            Log.request(f"Error placing order with stop-loss/take-profit: {e}")
            return None

    def is_market_open(self):
        """
        Méthode pour vérifier si le marché est ouvert.
        ---------------------------------------------
        """
        Log.request('Market status request..')
        return True

class KrakenFutures(Broker):#HS
    """
    Classe KrakenFutures pour les opérations avec le broker Kraken pour les futures.

    Kraken Futures est une plateforme d'échange pour les futures

    --------------------------------------------------------
    Methods:
    --------
    connect_ws(data_manager, tickers, stocks=True):
        Connexion au websocket de Kraken Futures.

    start_event_loop():
        Démarre la boucle d'événements asynchrones.

    subscribe_to_updates(tickers):
        Souscrit aux mises à jour des tickers.

    stop():
        Arrête la souscription aux mises à jour des tickers.

    process_message(message):
        Traite les messages reçus du websocket.

    get_actual_bar(assets):
        Obtient les dernières barres de données.

    bars_from_today_to(asset, stocks, timeframe, day_back=0, hour_back=0, minute_back=0):
        Obtient les barres historiques des données.

    get_account_info():
        Obtient les informations du compte.

    get_cash():
        Obtient les informations sur les liquidités.

    get_positions(asset):
        Obtient les positions ouvertes.

    place_order(asset, quantity, side, id='default'):
        Passe une commande.

    place_order_sl(asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        Passe une commande avec stop-loss et/ou take-profit.

    is_market_open():
        Vérifie si le marché est ouvert.
    --------------------------------------------------------
    """
    def __init__(self, name: str, api_key: str, api_secret: str, broker_type: str):
        super().__init__(name, api_key, api_secret, broker_type)
        self.api = krakenex.API(key=api_key, secret=api_secret)
        self.ws_url = 'wss://futures.kraken.com/ws/v1'
        self.ws_task = None
        self.data_manager = None
        self.lock = threading.Lock()
        self.loop = None
        self.thread = None
        self.stop_event = asyncio.Event()

    def connect_ws(self, data_manager: DataManager, tickers: list[str], stocks: bool = True):
        """
        Méthode pour se connecter au websocket du broker Kraken Futures.
        --------------------------------------------------------
        Parameters:
        -----------
        data_manager : DataManager
            L'objet qui recevra les données.
        tickers : list[str]
            Liste des tickers à souscrire.
        stocks : bool
            Indique si les tickers sont des actions (True) ou des cryptos (False).
        --------------------------------------------------------
        """
        self.data_manager = data_manager
        self.start_event_loop()
        self.ws_task = asyncio.run_coroutine_threadsafe(self.subscribe_to_updates(tickers), self.loop)  # type: ignore

    def start_event_loop(self):
        """
        Méthode pour démarrer la boucle d'événements asynchrones.
        --------------------------------------------------------
        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()

    async def unsubscribe_all(self, tickers : list[str]):
        async with websockets.connect(self.ws_url) as websocket : 
            unsubscribe_message = {
                            "method": "unsubscribe",
                            "params": {
                                "channel": "ohlc",
                                "symbol": tickers,
                                "interval": 1
                            }
                        }
            await websocket.send(json.dumps(unsubscribe_message))

    async def subscribe_to_updates(self, tickers: list[str]):
        """
        Méthode pour souscrire aux mises à jour des tickers.
        ----------------------------------------------------
        Parameters:
        -----------
        tickers : list[str]
            Liste des tickers à souscrire.
        ----------------------------------------------------
        """
        Log.request('Subscription thread has been launched for Kraken Futures')
        while not self.stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    subscribe_message = {
                        "event": "subscribe",
                        "feed": "book",
                        "product_ids": tickers
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    Log.request(f"Sent subscribe message: {subscribe_message}")

                    while not self.stop_event.is_set():
                        response = await websocket.recv()
                        message = json.loads(response)
                        self.process_message(message)

            except websockets.ConnectionClosedError as e:
                Log.request(f"Connection closed with error: {e}")
                Log.request("Attempting to reconnect in 5 seconds...")
                await asyncio.sleep(5)
            except json.JSONDecodeError as e:
                Log.request(f"Error decoding JSON: {e}")
            except Exception as e:
                Log.request(f"An unexpected error occurred: {e}")

    async def stop(self):
        """
        Méthode pour arrêter la souscription aux mises à jour des tickers.
        ------------------------------------------------------------------
        """
        self.stop_event.set()

    def process_message(self, message):
        """
        Méthode pour traiter les messages reçus du websocket.
        -----------------------------------------------------
        Parameters:
        -----------
        message : dict
            Message reçu du websocket.
        -----------------------------------------------------
        """
        try:
            if 'feed' in message and message['feed'] == 'book':
                data = message['data']
                ticker = data['product_id']
                new_bar = {
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'close': data['close'],
                    'volume': data['volume'],
                    'timestamp': pd.Timestamp(data['timestamp'], unit='s'),
                    'symbol': ticker,
                }

                with self.lock:
                    self.data_manager.handle_ws_message(new_bar)  # type: ignore

            elif 'event' in message and message['event'] == 'heartbeat':
                pass
            else:
                Log.request(f"Unexpected message format: {message}")
        except KeyError as e:
            Log.request(f"Key error processing message: {e}")
        except Exception as e:
            Log.request(f"Error processing message: {e}")

    def get_actual_bar(self, assets: list[str]):
        """
        Méthode pour obtenir les dernières barres de données.
        -----------------------------------------------------
        Parameters:
        -----------
        assets : list[str]
            Liste des actifs à obtenir.
        -----------------------------------------------------
        """
        data = {}
        for asset in assets:
            try:
                response = self.api.query_public('OHLC', {'pair': asset, 'interval': 1})
                if 'error' in response and response['error']:
                    Log.request(f"Error fetching data for {asset}: {response['error']}")
                    continue
                ohlc_data = response['result'][asset]
                latest_bar = ohlc_data[-1]
                data[asset] = {
                    'open': float(latest_bar[1]),
                    'high': float(latest_bar[2]),
                    'low': float(latest_bar[3]),
                    'close': float(latest_bar[4]),
                    'volume': float(latest_bar[6]),
                    'timestamp': datetime.utcfromtimestamp(int(latest_bar[0])).isoformat(),
                    'symbol': asset,
                }
            except Exception as e:
                Log.request(f"Error fetching actual bar for {asset}: {e}")
        Log.request('Data from broker received')
        return data

    def bars_from_today_to(self, assets: list[str], stocks : bool, timeframe: str, day_back: int = 0, hour_back: int = 0, minute_back: int = 0):
        """
        Méthode pour obtenir les barres historiques des données.
        --------------------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à obtenir.
        timeframe : int
            Intervalle de temps pour les barres.
        day_back : int, optional
            Nombre de jours en arrière.
        hour_back : int, optional
            Nombre d'heures en arrière.
        minute_back : int, optional
            Nombre de minutes en arrière.
        --------------------------------------------------------
        """
        try:
            start_time = (datetime.now() - timedelta(days=day_back, hours=hour_back , minutes=minute_back)).timestamp()
            standardized_data = []

            for asset in assets:
                request = {
                    'pair': asset,
                    'interval': conversion_map()[timeframe],
                    'since': int(start_time)
                }
                response = self.api.query_public('OHLC', request)
                if 'error' in response and response['error']:
                    Log.request(f"Error fetching data for {asset}: {response['error']}")
                    continue

                data = response['result'][asset]
                
                # Standardize the data
                for bar in data:
                    standardized_data.append({
                        'open': float(bar[1]),
                        'high': float(bar[2]),
                        'low': float(bar[3]),
                        'close': float(bar[4]),
                        'volume': float(bar[6]),
                        'timestamp': datetime.fromtimestamp(bar[0])-timedelta(hours=2),
                        'symbol': asset
                    })

            return standardized_data

        except Exception as e:
            Log.request(f"Error fetching bars: {e}")
            return []

    def get_account_info(self):
        """
        Méthode pour obtenir les informations du compte.
        ------------------------------------------------
        """
        try:
            Log.request('Asking account info..')
            return self.api.query_private('Balance')
        except Exception as e:
            Log.request(f"Error fetching account info: {e}")
            return None

    def get_cash(self):
        """
        Méthode pour obtenir les informations sur les liquidités.
        ---------------------------------------------------------
        """
        try:
            Log.request('Asking cash info..')
            balance = self.get_account_info()
            return balance.get('ZUSD', 0.0)  # type: ignore # Assuming USD as base currency
        except Exception as e:
            Log.request(f"Error fetching cash info: {e}")
            return None

    def get_positions(self, asset: str):
        """
        Méthode pour obtenir les positions ouvertes.
        --------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à obtenir.
        --------------------------------------------
        """
        try:
            Log.request('Asking open positions..')
            balance = self.get_account_info()
            return balance.get(asset, 0.0) # type: ignore
        except Exception as e:
            Log.request(f"Error fetching positions: {e}")
            return None

    def place_order(self, asset: str, quantity: float, side: str, id: str = 'default'):
        """
        Méthode pour passer une commande.
        ---------------------------------
        Parameters:
        -----------
        asset : str
            Actif à acheter/vendre.
        quantity : float
            Quantité à acheter/vendre.
        side : str
            Type d'opération ('buy' ou 'sell').
        id : str, optional
            Identifiant de la commande.
        ---------------------------------
        """
        try:
            order = {
                'pair': asset,
                'type': side,
                'ordertype': 'market',
                'volume': quantity
            }
            Log.request(f'Order submit to the broker: {side} {quantity} {asset}')
            res = self.api.query_private('AddOrder', order)
            Log.request(f'Order answer for {side} {quantity} {asset} received: {res}')
            Log.order(f'{id} - {side} {quantity} {asset}')
            return res
        except Exception as e:
            Log.request(f"Error placing order: {e}")
            return None

    def place_order_sl(self, asset: str, quantity: float, side: str, take_profit: float | None = None, stop_loss: float | None = None, id: str = 'default'):
        """
        Méthode pour passer une commande avec stop-loss et/ou take-profit.
        ------------------------------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à acheter/vendre.
        quantity : float
            Quantité à acheter/vendre.
        side : str
            Type d'opération ('buy' ou 'sell').
        take_profit : float, optional
            Prix de prise de profit.
        stop_loss : float, optional
            Prix de stop-loss.
        id : str, optional
            Identifiant de la commande.
        ------------------------------------------------------------------
        """
        try:
            order = {
                'pair': asset,
                'type': side,
                'ordertype': 'stop-loss-limit' if stop_loss else 'take-profit-limit' if take_profit else 'market',
                'volume': quantity,
                'price': take_profit or stop_loss
            }
            Log.request(f'Send {id} - {side} {quantity} {asset}..')
            res = self.api.query_private('AddOrder', order)
            Log.request(f'{id} - {side} {quantity} {asset} received: {res}')
            Log.order(f'{id} - {side} {quantity} {asset}')
            return res
        except Exception as e:
            Log.request(f"Error placing order with stop-loss/take-profit: {e}")
            return None

    def is_market_open(self):
        """
        Méthode pour vérifier si le marché est ouvert.
        ---------------------------------------------
        """
        Log.request('Market status request..')
        return True

class MEXCFutures(Broker):#HS
    """
    Classe MexcFutures pour les opérations avec le broker MEXC.

    MEXC est une plateforme d'échange pour les futures

    --------------------------------------------------------
    Methods:
    --------
    connect_ws(data_manager, tickers, stocks=True):
        Connexion au websocket de MEXC.

    start_event_loop():
        Démarre la boucle d'événements asynchrones.

    subscribe_to_updates(tickers):
        Souscrit aux mises à jour des tickers.

    stop():
        Arrête la souscription aux mises à jour des tickers.

    process_message(message):
        Traite les messages reçus du websocket.

    get_actual_bar(assets):
        Obtient les dernières barres de données.

    bars_from_today_to(asset, stocks, timeframe, day_back=0, hour_back=0, minute_back=0):
        Obtient les barres historiques des données.

    get_account_info():
        Obtient les informations du compte.

    get_cash():
        Obtient les informations sur les liquidités.

    get_positions(asset):
        Obtient les positions ouvertes.

    place_order(asset, quantity, side, id='default'):
        Passe une commande.

    place_order_sl(asset, quantity, side, take_profit=None, stop_loss=None, id='default'):
        Passe une commande avec stop-loss et/ou take-profit.

    is_market_open():
        Vérifie si le marché est ouvert.
    --------------------------------------------------------
    """
    def __init__(self, name: str, api_key: str, api_secret: str, broker_type: str):
        super().__init__(name, api_key, api_secret, broker_type)
        self.ws_url = 'wss://contract.mexc.com/edge'
        self.api_url = 'https://contract.mexc.com/api/v1'
        self.ws_task = None
        self.data_manager = None
        self.lock = threading.Lock()
        self.loop = None
        self.thread = None
        self.stop_event = asyncio.Event()
        self.temp: dict = {}

    def connect_ws(self, data_manager: DataManager, tickers: list[str], stocks: bool = True):
        """
        Méthode pour se connecter au websocket du broker MEXC.
        --------------------------------------------------------
        Parameters:
        -----------
        data_manager : DataManager
            L'objet qui recevra les données.
        tickers : list[str]
            Liste des tickers à souscrire.
        stocks : bool
            Indique si les tickers sont des actions (True) ou des cryptos (False).
        --------------------------------------------------------
        """
        self.data_manager = data_manager
        self.start_event_loop()
        self.ws_task = asyncio.run_coroutine_threadsafe(self.subscribe_to_updates(tickers), self.loop)  # type: ignore

    def start_event_loop(self):
        """
        Méthode pour démarrer la boucle d'événements asynchrones.
        --------------------------------------------------------
        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()

    async def subscribe_to_updates(self, tickers: list[str]):
        """
        Méthode pour souscrire aux mises à jour des tickers.
        ----------------------------------------------------
        Parameters:
        -----------
        tickers : list[str]
            Liste des tickers à souscrire.
        ----------------------------------------------------
        """
        Log.request('Subscription thread has been launched for MEXC')
        while not self.stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    for ticker in tickers:
                        corrected_ticker = ticker.replace("/", "_")  # Remplacer les slash par des underscores
                        subscribe_message = {
                            "method": "sub.kline",
                            "param": {
                                "symbol": corrected_ticker,
                                "interval": "Min1"
                            }
                        }
                        await websocket.send(json.dumps(subscribe_message))
                        Log.request(f"Sent subscribe message: {subscribe_message}")

                    while not self.stop_event.is_set():
                        response = await websocket.recv()
                        message = json.loads(response)
                        self.process_message(message)

            except websockets.ConnectionClosedError as e:
                Log.request(f"Connection closed with error: {e}")
                Log.request("Attempting to reconnect in 5 seconds...")
                await asyncio.sleep(5)
            except json.JSONDecodeError as e:
                Log.request(f"Error decoding JSON: {e}")
            except Exception as e:
                Log.request(f"An unexpected error occurred: {e}")

    async def stop(self):
        """
        Méthode pour arrêter la souscription aux mises à jour des tickers.
        ------------------------------------------------------------------
        """
        self.stop_event.set()

    def process_message(self, message):
        """
        Méthode pour traiter les messages reçus du websocket.
        -----------------------------------------------------
        Parameters:
        -----------
        message : dict
            Message reçu du websocket.
        -----------------------------------------------------
        """
        try:
            if message['channel'] == 'push.kline':
                data = message['data']
                ticker = data['symbol']
                new_bar = {
                    'open': data['o'],
                    'high': data['h'],
                    'low': data['l'],
                    'close': data['c'],
                    'volume': data['q'],
                    'timestamp': pd.Timestamp(data['t'], unit='s'),
                    'symbol': ticker.replace("_","/"),
                }
                with self.lock:
                    self.data_manager.handle_ws_message(new_bar)  # type: ignore
            elif message['channel'] == 'pong':
                pass
            else:
                Log.request(f"Unexpected message format: {message}")
        except KeyError as e:
            Log.request(f"Key error processing message: {e}")
        except Exception as e:
            Log.request(f"Error processing message: {e}")

    def get_actual_bar(self, assets: list[str]):
        """
        Méthode pour obtenir les dernières barres de données.
        -----------------------------------------------------
        Parameters:
        -----------
        assets : list[str]
            Liste des actifs à obtenir.
        -----------------------------------------------------
        """
        all_data = {}
        end_time = datetime.now()
        start_time=end_time-timedelta(minutes=1)
        for asset in assets:
            try:
                response = requests.get(f"{self.api_url}/contract/kline/index_price/{asset.replace('/','_')}?interval=Min1&start={int(start_time.timestamp())}&end={int(end_time.timestamp())}")
                response.raise_for_status()
                data = response.json()['data']
                all_data[asset]={
                        'open': data['open'][0],
                        'high': data['high'][0],
                        'low': data['low'][0],
                        'close': data['close'][0],
                        'volume': data['vol'][0],
                        'timestamp': datetime.fromtimestamp(data['time'][0])-timedelta(hours=2),
                        'symbol': asset
                    }
            except Exception as e:
                Log.request(f"Error fetching actual bar for {asset}: {e}")
        Log.request('Data from broker received')
        return all_data

    def bars_from_today_to(self, assets: list[str], stocks : bool, timeframe: str, day_back: int = 0, hour_back: int = 0, minute_back: int = 0):
        """
        Méthode pour obtenir les barres historiques des données.
        --------------------------------------------------------
        Parameters:
        -----------
        asset : list[str]
            Actif à obtenir.
        stocks : bool
            Actifs ou autres ?
        timeframe : int
            Intervalle de temps pour les barres.
        day_back : int, optional
            Nombre de jours en arrière.
        hour_back : int, optional
            Nombre d'heures en arrière.
        minute_back : int, optional
            Nombre de minutes en arrière.
        --------------------------------------------------------
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=day_back, hours=hour_back, minutes=minute_back)
            standardized_data = []

            for asset in assets:
                request_url = f"{self.api_url}/contract/kline/index_price/{asset.replace('/','_')}?interval={conversion_mexc_map()[timeframe]}&start={int(start_time.timestamp())}&end={int(end_time.timestamp())}"
                response = requests.get(request_url)
                response.raise_for_status()
                data = response.json()['data']
                # Standardize the data
                for i in range(len(data['time'])):
                    standardized_data.append({
                        'open': data['open'][i],
                        'high': data['high'][i],
                        'low': data['low'][i],
                        'close': data['close'][i],
                        'volume': data['vol'][i],
                        'timestamp': datetime.fromtimestamp(data['time'][i])-timedelta(hours=2),
                        'symbol': asset
                    })

            return standardized_data

        except Exception as e:
            Log.request(f"Error fetching bars: {e}")
            return []

    def get_account_info(self):
        """
        Méthode pour obtenir les informations du compte.
        ------------------------------------------------
        """
        try:
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            response = requests.get(f'{self.api_url}/private/account/assets', headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            Log.request(f"Error fetching account info: {e}")
            return None

    def get_cash(self):
        """
        Méthode pour obtenir les informations sur les liquidités.
        ---------------------------------------------------------
        """
        try:
            Log.request('Asking cash info..')
            account_info = self.get_account_info()
            for asset in account_info['data']: # type: ignore
                if asset['currency'] == 'USDT':
                    return asset['availableBalance']
            return 0.0
        except Exception as e:
            Log.request(f"Error fetching cash info: {e}")
            return None

    def get_positions(self, asset: str):
        """
        Méthode pour obtenir les positions ouvertes.
        --------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à obtenir.
        --------------------------------------------
        """
        try:
            Log.request('Asking open positions..')
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            response = requests.get(f'{self.api_url}/private/position/open_positions', headers=headers)
            response.raise_for_status()
            positions = response.json()['data']
            for position in positions:
                if position['symbol'] == asset:
                    return position
            return None
        except Exception as e:
            Log.request(f"Error fetching positions: {e}")
            return None

    def place_order(self, asset: str, quantity: float, side: str, id: str = 'default'):
        """
        Méthode pour passer une commande.
        ---------------------------------
        Parameters:
        -----------
        asset : str
            Actif à acheter/vendre.
        quantity : float
            Quantité à acheter/vendre.
        side : str
            Type d'opération ('buy' ou 'sell').
        id : str, optional
            Identifiant de la commande.
        ---------------------------------
        """
        try:
            order = {
                'symbol': asset,
                'price': 0,  # Market order
                'vol': quantity,
                'side': 1 if side == 'buy' else 2,
                'type': 5,  # Market order
                'openType': 1  # Isolated margin
            }
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            response = requests.post(f'{self.api_url}/private/order/submit', json=order, headers=headers)
            response.raise_for_status()
            Log.request(f'Order answer for {side} {quantity} {asset} received: {response.json()}')
            Log.order(f'{id} - {side} {quantity} {asset}')
            return response.json()
        except Exception as e:
            Log.request(f"Error placing order: {e}")
            return None

    def place_order_sl(self, asset: str, quantity: float, side: str, take_profit: float | None = None, stop_loss: float | None = None, id: str = 'default'):
        """
        Méthode pour passer une commande avec stop-loss et/ou take-profit.
        ------------------------------------------------------------------
        Parameters:
        -----------
        asset : str
            Actif à acheter/vendre.
        quantity : float
            Quantité à acheter/vendre.
        side : str
            Type d'opération ('buy' ou 'sell').
        take_profit : float, optional
            Prix de prise de profit.
        stop_loss : float, optional
            Prix de stop-loss.
        id : str, optional
            Identifiant de la commande.
        ------------------------------------------------------------------
        """
        try:
            order = {
                'symbol': asset,
                'price': 0,
                'vol': quantity,
                'side': 1 if side == 'buy' else 2,
                'type': 1 if take_profit or stop_loss else 5,  # Limit order or market order
                'openType': 1,  # Isolated margin
                'stopLossPrice': stop_loss,
                'takeProfitPrice': take_profit
            }
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            response = requests.post(f'{self.api_url}/private/order/submit', json=order, headers=headers)
            response.raise_for_status()
            Log.request(f'{id} - {side} {quantity} {asset} received: {response.json()}')
            Log.order(f'{id} - {side} {quantity} {asset}')
            return response.json()
        except Exception as e:
            Log.request(f"Error placing order with stop-loss/take-profit: {e}")
            return None

    def is_market_open(self):
        """
        Méthode pour vérifier si le marché est ouvert.
        ---------------------------------------------
        """
        Log.request('Market status request..')
        return True
