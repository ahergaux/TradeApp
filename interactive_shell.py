import os
import sys
import threading
import time

# Ajoutez le répertoire de votre projet au chemin de recherche des modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importez les classes et fonctions nécessaires de votre application
from tradeAPP.DataManager import DataManager
from tradeAPP.BrokerHandler import BrokerHandler
import tradeAPP.TickersHandler as TickersHandler
from tradeAPP.AutomationHandler import AutomationHandler
from tradeAPP.strategies import Strategies
import tradeAPP.enums as enums

# Importez les modules spécifiques contenant des fonctions
from tradeAPP.log import Log
from tradeAPP.broker import *
from tradeAPP.automation import Automation
from tradeAPP.main import Trader

from unittest.mock import MagicMock

# Initialisez les objets nécessaires pour les différentes classes
def initialize_data_manager():
    broker_instance = MagicMock()  # Remplacez par un mock ou une instance appropriée
    data_manager = DataManager(broker_instance, stocks=True, tickers=['BTCUSD', 'ETHUSD'])
    return data_manager

def initialize_broker_handler():
    broker_handler = BrokerHandler()
    return broker_handler

def initialize_broker_mexc():
    mexc = MEXCFutures("mexc","mx0vglic3QRRBEbBap","42563b247ee04c2bbba8b2c7363a1ef5","MEXCFutures")
    return mexc

def initialize_broker_alpaca():
    alpaca = Alpaca("alpaca","PK0EAYZK2FC6FK9Y7XFA","Rysuf3yBmFTmCg76XpozzwPDGPDooiZVCqPZJWry","Alpaca")
    return alpaca

def initialize_broker_kraken():
    kraken = Kraken("kraken","bQmD3gyvGv9XVYi1voCOEYapLLJ98AAwoHg1PZn2uJ1emJIezBEhPd0G","zwgm6X3BJTGuVIL0OmajsbkE0f9leIMAT5VrYmhmmvQuNHFX9P5v+/gcv/W0/xmQsYfQgxini7EX7jdjsMndVw==","Kraken")
    return kraken

def initialize_automation_handler():
    automation_handler = AutomationHandler()
    return automation_handler

def initialize_strategies():
    strategies_instance = Strategies()
    return strategies_instance

# Exemple de fonction de test avec DataManager
def test_transform_data(data_manager):
    # Mock les méthodes et attributs nécessaires
    data_manager.broker.is_market_open.return_value = True
    data_manager.new_bar = {
        'BTCUSD': {'timestamp': '2024-07-23 12:00:00', 'open': 30000, 'high': 30500, 'low': 29900, 'close': 30300, 'volume': 100},
        'ETHUSD': {'timestamp': '2024-07-23 12:00:00', 'open': 2000, 'high': 2050, 'low': 1990, 'close': 2030, 'volume': 50}
    }

    # Appelez la méthode transform_data et affichez les résultats
    threading.Thread(target=data_manager.transform_data).start()
    time.sleep(2)  # Attendez que les données soient transformées
    print_data(data_manager)

def print_data(data_manager):
    for ticker, data in data_manager.data.items():
        print(f"Data for {ticker}:")
        for timeframe, bars in data.items():
            print(f"  Timeframe {timeframe}:")
            for bar in bars:
                print(f"    {bar}")

# Ajoutez une fonction pour l'interaction dans le shell
def interactive_shell():
    # Initialisation des objets nécessaires
    data_manager = initialize_data_manager()
    broker_handler = initialize_broker_handler()
    automation_handler = initialize_automation_handler()
    strategies_instance = initialize_strategies()
    mexc=initialize_broker_mexc()
    alpaca=initialize_broker_alpaca()
    kraken=initialize_broker_kraken()

    # Objets disponibles dans le shell interactif
    available_objects = {
        "data_manager": data_manager,
        "broker_handler": broker_handler,
        "tickers_handler": TickersHandler,
        "automation_handler": automation_handler,
        "strategies_instance": strategies_instance,
        "log": Log,
        "mexc": mexc,
        "alpaca" : alpaca,
        "kraken": kraken,
        "automation": Automation,
        "trader": Trader,
        "test_transform_data": test_transform_data,
        "print_data": print_data
    }

    print("Bienvenue dans le shell interactif. Tapez 'exit' pour quitter.")
    while True:
        try:
            command = input(">>> ")
            if command == "exit":
                break
            exec(command, globals(), available_objects)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    interactive_shell()