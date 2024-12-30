from .broker import Broker
from .BrokerHandler import BrokerHandler
from .automation import Automation
from .AutomationHandler import AutomationHandler
from .enums import strategy_map, broker_map
from .DataManager import DataManager
from .StrategyThreads import StrategyThread
from .log import Log

class Trader:
    def __init__(self):
        """
        Initialise le Trader avec les brokers et automations enregistrés.
        """
        Log.usr('Initialisation du Trader...')
        try:
            self.brokers = BrokerHandler.read_brokers()
            self.automations = AutomationHandler.read_automations()
            self.nbreAuto = len(self.automations)
            self.threads = []
            self.data_managers = {}
            Log.usr('Initialisation terminée.')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'initialisation: {e}')

    def get_all_tickers(self, broker_type, stocks):
        """
        Retourne tous les tickers pour un type de broker et une catégorie donnée.
        """
        Log.usr('Récupération des tickers...')
        tickers = []
        try:
            for automation in self.automations:
                if automation.broker.broker_type == broker_type and automation.stocks == stocks:
                    tickers += automation.ticker
            Log.usr(f'Tickers récupérés: {tickers}')
        except Exception as e:
            Log.usr(f'Erreur lors de la récupération des tickers: {e}')
        return tickers

    def start_automation(self, automation_id):
        """
        Démarre une automatisation donnée par son ID.
        """
        try:
            Log.usr(f'Démarrage de l\'automation {automation_id}...')
            automation = self.automations[automation_id - 1]
            automation.status = 'active'
            data_manager = self.data_recup(automation.broker, automation.stocks)
            AutomationHandler.write_automations(self.automations)
            strategy_thread = StrategyThread(automation.strategies, automation.ticker, automation.timeframe, automation.broker, data_manager) # type: ignore
            strategy_thread.start()
            self.threads.append(strategy_thread)
            Log.usr(f'Automation {automation_id} démarrée.')
        except IndexError:
            Log.usr(f'ID d\'automation {automation_id} invalide.')
        except Exception as e:
            Log.usr(f'Erreur lors du démarrage de l\'automation {automation_id}: {e}')

    def stop_automation(self, automation_id):
        """
        Arrête une automatisation donnée par son ID.
        """
        try:
            Log.usr(f'Arrêt de l\'automation {automation_id}...')
            automation = self.automations[automation_id - 1]
            automation.status = 'inactive'
            AutomationHandler.write_automations(self.automations)
            for thread in self.threads:
                if thread.strategy == automation.strategies and thread.broker.name == automation.broker.name:
                    thread.stop()
                    self.threads.remove(thread)
                    break
            Log.usr(f'Automation {automation_id} arrêtée.')
            if not any(a.status == 'active' and a.broker.name == automation.broker.name for a in self.automations):
                self.stop_data_manager(automation.broker.name)
        except IndexError:
            Log.usr(f'ID d\'automation {automation_id} invalide.')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'arrêt de l\'automation {automation_id}: {e}')

    def load_brokers(self):
        """
        Charge les brokers depuis les fichiers de configuration.
        """
        try:
            self.brokers = BrokerHandler.read_brokers()
            Log.usr('Brokers chargés.')
        except Exception as e:
            Log.usr(f'Erreur lors du chargement des brokers: {e}')

    def save_brokers(self):
        """
        Sauvegarde les brokers dans les fichiers de configuration.
        """
        try:
            BrokerHandler.write_brokers(self.brokers)
            Log.usr('Brokers sauvegardés.')
        except Exception as e:
            Log.usr(f'Erreur lors de la sauvegarde des brokers: {e}')

    def add_broker(self, name, api_key, api_secret, broker_type):
        """
        Ajoute un nouveau broker.
        """
        try:
            broker = self.create_broker_instance(broker_type, name, api_key, api_secret)
            self.brokers.append(broker)
            BrokerHandler.add_broker(broker)
            Log.usr(f'Broker ajouté: Nom: {name}, API Key: {api_key}, Broker: {broker_type}')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'ajout du broker: {e}')

    def create_broker_instance(self, broker_type, name, api_key, api_secret):
        """
        Crée une instance de broker selon le type donné.
        """
        try:
            return broker_map()[broker_type](name, api_key, api_secret, broker_type)
        except KeyError:
            Log.usr(f'Type de broker {broker_type} invalide.')
        except Exception as e:
            Log.usr(f'Erreur lors de la création du broker: {e}')

    def data_recup(self, broker, stocks):
        """
        Récupère les données pour un broker et une catégorie donnée.
        """
        try:
            if broker.broker_type not in self.data_managers:
                data_manager = DataManager(broker, stocks, self.get_all_tickers(broker.broker_type, stocks))
                self.data_managers[broker.broker_type] = data_manager
                Log.data(f'DataManager {broker.broker_type} lancée')
            else:
                data_manager = self.data_managers[broker.broker_type]
                if broker!=data_manager.broker :
                    data_manager.actualize()
                    Log.data(f'DataManager {broker.broker_type} actualisé')

            return data_manager
        except Exception as e:
            Log.data(f'Erreur lors de la récupération des données pour le broker {broker.name}: {e}')

    def stop_data_manager(self, broker_type):
        """
        Arrête le gestionnaire de données pour un type de broker donné.
        """
        try:
            if broker_type in self.data_managers:
                self.data_managers[broker_type].stop()
                del self.data_managers[broker_type]
                Log.data(f'Gestionnaire de données arrêté pour le broker {broker_type}')
        except Exception as e:
            Log.data(f'Erreur lors de l\'arrêt du gestionnaire de données pour le broker {broker_type}: {e}')

    def remove_broker(self, name):
        """
        Supprime un broker par son nom.
        """
        try:
            self.brokers = [broker for broker in self.brokers if broker.name != name]
            if name in self.data_managers:
                self.stop_data_manager(name)
            BrokerHandler.remove_broker(name)
            Log.usr(f'Broker {name} supprimé')
        except Exception as e:
            Log.usr(f'Erreur lors de la suppression du broker {name}: {e}')

    def add_automation(self, strategy_class_name, ticker_file, timeframe, broker_name, stocks):
        """
        Ajoute une nouvelle automatisation.
        """
        try:
            self.nbreAuto += 1
            automation = Automation(self.nbreAuto, strategy_class_name, ticker_file, timeframe, broker_name, stocks)
            self.automations.append(automation)
            AutomationHandler.write_automations(self.automations)
            Log.usr(f'Automation ajoutée, ID: {self.nbreAuto}')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'ajout de l\'automation: {e}')

    def remove_automation(self, automation_id):
        """
        Supprime une automatisation par son ID.
        """
        try:
            self.stop_automation(automation_id)
            self.automations.pop(automation_id - 1)
            AutomationHandler.write_automations(self.automations)
            Log.usr(f'Automation supprimée, ID: {automation_id}')
        except IndexError:
            Log.usr(f'ID d\'automation {automation_id} invalide.')
        except Exception as e:
            Log.usr(f'Erreur lors de la suppression de l\'automation {automation_id}: {e}')

    def display_automations(self):
        """
        Affiche toutes les automatisations.
        """
        try:
            for i, automation in enumerate(self.automations):
                print(f"Automation {automation.id}: Strategies: {automation.strategies}, Status: {automation.status}")
            Log.usr('Affichage des automatisations terminé.')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'affichage des automatisations: {e}')

    def display_strategies(self):
        """
        Affiche toutes les stratégies disponibles.
        """
        try:
            for strategy_name in strategy_map():
                print(strategy_name)
            Log.usr('Affichage des stratégies terminé.')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'affichage des stratégies: {e}')

    def display_brokers(self):
        """
        Affiche tous les brokers disponibles.
        """
        try:
            for broker in self.brokers:
                print(f"Name: {broker.name}, API Key: {broker.api_key}, Broker: {broker.broker_type}")
            Log.usr('Affichage des brokers terminé.')
        except Exception as e:
            Log.usr(f'Erreur lors de l\'affichage des brokers: {e}')

    def menu(self):
        """
        Affiche le menu principal et gère les entrées utilisateur.
        """
        while True:
            try:
                print("\n\n\n\tMenu:\n")
                print("0. Afficher les stratégies")
                print("1. Ajouter une automatisation")
                print("2. Supprimer une automatisation")
                print("3. Afficher les automatisations")
                print("4. Ajouter un broker")
                print("5. Supprimer un broker")
                print("6. Afficher les brokers")
                print("7. Lancer une automatisation")
                print("8. Arrêter une automatisation")
                print("9. Lancer/Actualiser la récupération de données")
                print('10. Stopper la récupération de données')
                print("11. Quitter et fermer tous les threads") 
                choice = input("Choisissez une option: ")
                if choice == '0':
                    self.display_strategies()
                elif choice == '1':
                    strategy_class_name = input("Nom de la stratégie: ")
                    ticker_file = input("Nom de la colonne des tickers: ")
                    timeframe = input("Timeframe (M, 5M, 15M, H, D): ")
                    broker_name = input("Nom du broker: ")
                    stocks = None
                    inp = input("Actions ? (True/False)").strip().lower()
                    stocks = inp == 'true'
                    self.add_automation(strategy_class_name, ticker_file, timeframe, broker_name, stocks)
                elif choice == '2':
                    automation_id = int(input("ID de l'automatisation à supprimer: "))
                    self.remove_automation(automation_id)
                elif choice == '3':
                    self.display_automations()
                elif choice == '4':
                    name = input("Nom du broker: ")
                    api_key = input("Clé API: ")
                    api_secret = input("Secret API: ")
                    broker_type = input("Type de broker: ")
                    self.add_broker(name, api_key, api_secret, broker_type)
                elif choice == '5':
                    name = input("Nom du broker à supprimer: ")
                    self.remove_broker(name)
                elif choice == '6':
                    self.display_brokers()
                elif choice == '7':
                    automation_id = int(input("ID de l'automatisation à lancer:"))
                    self.start_automation(automation_id)
                elif choice == '8':
                    automation_id = int(input("ID de l'automatisation à stopper:"))
                    self.stop_automation(automation_id)
                elif choice == '9':
                    broker_name = input('Nom du broker :')
                    stocks = None
                    inp = input("Actions ? (True/False)").strip().lower()
                    stocks = inp == 'true'
                    brokers = BrokerHandler.read_brokers()
                    broker = next((b for b in brokers if b.name == broker_name), None)
                    if broker:
                        self.data_recup(broker, stocks)
                    else:
                        Log.usr(f'Broker {broker_name} non trouvé.')
                elif choice == '10':
                    broker_type = input('Type du broker :')
                    self.stop_data_manager(broker_type)
                elif choice == '11':
                    for auto in self.automations:
                        if auto.status == 'active':
                            self.stop_automation(auto.id)
                    quit()
                else:
                    print("Option invalide, veuillez réessayer.")
            except Exception as e:
                Log.usr(f'Erreur dans le menu: {e}')

def main():
    """
    Point d'entrée principal du programme.
    """
    Log.usr('/|\\ Program launch /|\\')
    Log.request('/|\\ Program launch /|\\')
    Log.data('/|\\ Program launch /|\\')
    Log.auto('/|\\ Program launch /|\\')
    
    try:
        trader = Trader()
        trader.menu()

        #testAlpaca()
        #testKraken()
        #testMEXC()
    except Exception as e:
        Log.usr(f'Erreur lors du lancement du programme: {e}')
"""
def testKraken():
    
    #Fonction de test pour Kraken.
    
    try:
        a = KrakenFutures('truc', 'bQmD3gyvGv9XVYi1voCOEYapLLJ98AAwoHg1PZn2uJ1emJIezBEhPd0G', 'zwgm6X3BJTGuVIL0OmajsbkE0f9leIMAT5VrYmhmmvQuNHFX9P5v+/gcv/W0/xmQsYfQgxini7EX7jdjsMndVw==', 'Kraken')
        #print(a.get_positions('BTC/USD'))
        print(a.bars_from_today_to(["BTC/USD"],False,'M',0,0,3))
        #print(a.get_actual_bar(["BTC/USDT","ETH/USDT"]))
        #print(a.get_account_info())
    except Exception as e:
        Log.usr(f'Erreur lors du test Kraken: {e}')


def testAlpaca():
    
    #Fonction de test pour Alpaca.
    
    try:
        a = Alpaca('alpaca', 'PK0EAYZK2FC6FK9Y7XFA', 'Rysuf3yBmFTmCg76XpozzwPDGPDooiZVCqPZJWry', 'Alpaca')
        #print(a.bars_from_today_to(["BTC/USD"],False,'M',0,0,3))
        #print(a.get_account_info())
        #print(a.get_actual_bar(["BTC/USDT","ETH/USDT"],False))
        print(a.get_account_info())
    except Exception as e:
        Log.usr(f'Erreur lors du test Kraken: {e}')
    


def testMEXC():
    
    #Fonction de test pour Alpaca.
    
    try:
        a = MEXCFutures('mexc', 'mx0vglic3QRRBEbBap', '42563b247ee04c2bbba8b2c7363a1ef5', 'MEXCFutures')
        #print(a.bars_from_today_to(["BTC/USDT","ETH/USDT"],False,'M',0,0,2))
        #print(a.get_account_info())
        #print(a.get_actual_bar(["BTC/USDT","ETH/USDT"]))
        print(a.get_account_info())
    except Exception as e:
        Log.usr(f'Erreur lors du test Kraken: {e}')

"""
if __name__ == '__main__':
    main()
