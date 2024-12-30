import csv
from .log import Log
from .enums import FilesApp

def read_tickers(nom_colonne):
    """
    Read ticker values from a specific column in the CSV file.
    --------------------------------------------------
    Parameters:
    -----------
    nom_colonne : str
        The name of the column to read tickers from.
    --------------------------------------------------
    Returns:
    --------
    list
        A list of ticker values from the specified column.
    --------------------------------------------------
    """
    column_values = []
    try:
        with open(FilesApp.Tickers.value, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            
            # Verify if the column name exists in the CSV file
            if nom_colonne not in reader.fieldnames:
                raise ValueError(f"La colonne '{nom_colonne}' n'existe pas dans le fichier CSV.")
            
            for row in reader:
                if row[nom_colonne] is not None and row[nom_colonne] != '':
                    column_values.append(row[nom_colonne])
        Log.usr(f"Successfully read tickers from column '{nom_colonne}' in the CSV file.")
    except FileNotFoundError:
        Log.usr(f"The file {FilesApp.Tickers.value} was not found.")
    except ValueError as ve:
        Log.usr(ve)
    except Exception as e:
        Log.usr(f"Error occurred in TickersHandler/read_tickers: {e}")
    
    return column_values
