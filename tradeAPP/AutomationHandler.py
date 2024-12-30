from .automation import Automation
import os
import csv
from .enums import FilesApp, strategy_map
from .strategies import Strategies
from .log import Log

class AutomationHandler:
    """
    Classe AutomationHandler pour gérer la lecture et l'écriture des automatisations.
    --------------------------------------------------------------

    Methods:
    --------
    read_automations():
        Lit les automatisations à partir d'un fichier CSV.

    write_automations(automations):
        Écrit les automatisations dans un fichier CSV.
    --------------------------------------------------------------
    """

    @staticmethod
    def read_automations():
        """
        Lit les automatisations à partir d'un fichier CSV.
        --------------------------------------------------------------

        Returns:
        --------
            list: 
                Liste des instances de la classe Automation.
        --------------------------------------------------------------
        """
        automations = []
        try:
            if os.path.exists(FilesApp.Auto.value):
                with open(FilesApp.Auto.value, mode='r') as file:
                    Log.auto("Lecture du fichier des automatisations.")
                    reader = csv.DictReader(file, delimiter=';')
                    for row in reader:
                        id = int(row['id'])
                        broker_name = row['broker_name']
                        strategy_class_name = row['strategy_class']
                        tickers = row['tickers']
                        timeframe = row['timeframe']
                        status = row['status']
                        stocks = row['stocks'].lower() == 'true'
                        automation = Automation(id, strategy_class_name, tickers, timeframe, broker_name, stocks, status)
                        automations.append(automation)
                    Log.auto("Lecture des automatisations terminée avec succès.")
            else:
                Log.auto("Le fichier des automatisations n'existe pas.")
        except Exception as e:
            Log.auto(f"Erreur lors de la lecture des automatisations: {str(e)}")
        return automations

    @staticmethod
    def write_automations(automations):
        """
        Écrit les automatisations dans un fichier CSV.
        --------------------------------------------------------------

        Args:
        -----
            automations (list): 
                Liste des instances de la classe Automation à écrire dans le fichier.
        --------------------------------------------------------------
        """
        try:
            with open(FilesApp.Auto.value, mode='w', newline='') as file:
                Log.auto("Écriture des automatisations dans le fichier.")
                writer = csv.DictWriter(file, fieldnames=['id', 'strategy_class', 'tickers', 'timeframe', 'broker_name', 'stocks', 'status'],delimiter=';')
                writer.writeheader()
                for automation in automations:
                    writer.writerow({
                        'id': automation.id,
                        'strategy_class': automation.strategy_name,
                        'tickers': automation.tickers_column,
                        'timeframe': automation.timeframe,
                        'broker_name': automation.broker.name,
                        'stocks': automation.stocks,
                        'status': automation.status
                    })
                Log.auto("Écriture des automatisations terminée avec succès.")
        except Exception as e:
            Log.auto(f"Erreur lors de l'écriture des automatisations: {str(e)}")

def get_strategy_class(strategy_class_name):
    """
    Récupère la classe de stratégie correspondant au nom donné.
    --------------------------------------------------------------

    Args:
    -----
        strategy_class_name (str): 
            Nom de la classe de stratégie.

    Returns:
    --------
        type: 
            Classe de stratégie correspondante ou la classe par défaut Strategies.
    --------------------------------------------------------------
    """
    return strategy_map.get(strategy_class_name, Strategies)
