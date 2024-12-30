import os
import csv
from .broker import Broker
from .enums import FilesApp, broker_map
from .log import Log

class BrokerHandler:
    @staticmethod
    def read_brokers():
        """
        Lit les brokers depuis un fichier CSV et retourne une liste d'instances de brokers.
        --------------------------------------------------
        Returns:
        --------
        brokers : list
            Liste des instances de brokers.
        --------------------------------------------------
        """
        brokers = []
        try:
            if os.path.exists(FilesApp.Brokers.value):
                with open(FilesApp.Brokers.value, mode='r') as file:
                    reader = csv.DictReader(file,delimiter=';')
                    for row in reader:
                        broker = broker_map()[row['broker_type']](row['name'], row['api_key'], row['api_secret'], row['broker_type'])
                        brokers.append(broker)
                Log.usr(f"Successfully read {len(brokers)} brokers from the file.")
            else:
                Log.usr(f"File {FilesApp.Brokers.value} does not exist.")
        except Exception as e:
            Log.usr(f"Error reading brokers: {e}")
        return brokers

    @staticmethod
    def write_brokers(brokers):
        """
        Écrit la liste des brokers dans un fichier CSV.
        --------------------------------------------------
        Parameters:
        -----------
        brokers : list
            Liste des instances de brokers à écrire.
        --------------------------------------------------
        """
        try:
            with open(FilesApp.Brokers.value, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['name', 'api_key', 'api_secret', 'broker_type'],delimiter=';')
                writer.writeheader()
                for broker in brokers:
                    writer.writerow({
                        'name': broker.name,
                        'api_key': broker.api_key,
                        'api_secret': broker.api_secret,
                        'broker_type': broker.broker_type,
                    })
            Log.usr(f"Successfully wrote {len(brokers)} brokers to the file.")
        except Exception as e:
            Log.usr(f"Error writing brokers: {e}")

    @staticmethod
    def add_broker(broker):
        """
        Ajoute un broker à la liste et met à jour le fichier CSV.
        --------------------------------------------------
        Parameters:
        -----------
        broker : Broker
            Instance du broker à ajouter.
        --------------------------------------------------
        """
        try:
            brokers = BrokerHandler.read_brokers()
            brokers.append(broker)
            BrokerHandler.write_brokers(brokers)
            Log.usr(f"Successfully added broker: {broker.name}")
        except Exception as e:
            Log.usr(f"Error adding broker: {e}")

    @staticmethod
    def remove_broker(broker_name):
        """
        Supprime un broker de la liste et met à jour le fichier CSV.
        --------------------------------------------------
        Parameters:
        -----------
        broker_name : str
            Nom du broker à supprimer.
        --------------------------------------------------
        """
        try:
            brokers = BrokerHandler.read_brokers()
            brokers = [broker for broker in brokers if broker.name != broker_name]
            BrokerHandler.write_brokers(brokers)
            Log.usr(f"Successfully removed broker: {broker_name}")
        except Exception as e:
            Log.usr(f"Error removing broker: {e}")
