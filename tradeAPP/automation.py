from .broker import Broker
from .BrokerHandler import BrokerHandler
from .TickersHandler import read_tickers
from .strategies import *
from .enums import strategy_map
from .log import Log

class Automation:
    """
    Classe Automation pour gérer les stratégies de trading automatisées.
    --------------------------------------------------------------

    Attributes:
    -----------
        id (int): 
            Identifiant unique de l'automatisation.
        
        strategies (object): 
            Stratégies associées à l'automatisation.
        
        strategy_name (str): 
            Nom de la stratégie.
        
        tickers_column (str): 
            Colonne des tickers.
        
        timeframe (str): 
            Période de temps pour la stratégie.
        
        broker (Broker): 
            Broker utilisé pour l'automatisation.
        
        status (str): 
            Statut de l'automatisation ('active' ou 'inactive').
        
        thread (Thread): 
            Thread pour l'exécution de l'automatisation.
        
        stocks (bool): 
            Indicateur si l'automatisation concerne les actions.
        
        ticker (list): 
            Liste des tickers.
    --------------------------------------------------------------
    """

    def __init__(self, id: int, strategies_name: str, tickers_column: str, timeframe: str, broker_name: str, stocks: bool, status: str = 'inactive'):
        """
        Initialise une nouvelle instance de la classe Automation.
        --------------------------------------------------------------

        Args:
        -----
            id (int): 
                Identifiant unique de l'automatisation.
            
            strategies_name (str): 
                Nom de la stratégie.
            
            tickers_column (str): 
                Colonne des tickers.
            
            timeframe (str): 
                Période de temps pour la stratégie.
            
            broker_name (str): 
                Nom du broker.
            
            stocks (bool): 
                Indicateur si l'automatisation concerne les actions.
            
            status (str): 
                Statut de l'automatisation ('active' ou 'inactive').
        --------------------------------------------------------------
        """
        try:
            Log.auto(f"Initialisation de l'automatisation ID: {id}")
            self.id: int = id
            self.strategies = strategy_map()[strategies_name]
            self.strategy_name = strategies_name
            self.tickers_column: str = tickers_column
            self.timeframe: str = timeframe
            self.broker: Broker = self.get_broker(broker_name)
            self.status: str = status
            self.thread = None
            self.stocks: bool = stocks
            self.ticker = read_tickers(self.tickers_column)
            Log.auto(f"Automatisation ID: {id} initialisée avec succès.")
        except Exception as e:
            Log.auto(f"Erreur lors de l'initialisation de l'automatisation ID: {id} - {str(e)}")

    def get_broker(self, broker_name) -> Broker:
        """
        Récupère l'instance du broker correspondant au nom donné.
        --------------------------------------------------------------

        Args:
        -----
            broker_name (str): 
                Nom du broker.

        Returns:
        --------
            Broker: 
                Instance du broker trouvé.
        
        Raises:
        -------
            ValueError: 
                Si aucun broker n'est trouvé.
        --------------------------------------------------------------
        """
        try:
            Log.auto(f"Récupération du broker: {broker_name}")
            brokers = BrokerHandler.read_brokers()
            broker: Broker = next((b for b in brokers if b.name == broker_name))
            if broker is None:
                raise ValueError(f"Broker {broker_name} non trouvé.")
            Log.auto(f"Broker {broker_name} récupéré avec succès.")
            return broker
        except Exception as e:
            Log.auto(f"Erreur lors de la récupération du broker {broker_name} - {str(e)}")
            return None # type: ignore
