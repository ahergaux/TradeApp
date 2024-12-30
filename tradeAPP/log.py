import logging

class Log:
    usr_log = None
    auto_log = None
    data_log = None
    request_log = None
    order_log = None

    @staticmethod
    def setup_loggers():
        # Configuration de base du logger
        logging.basicConfig(filename='logs/trading.log',
                            level=logging.INFO,
                            format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')

        # Création de loggers spécifiques pour chaque type de tâche
        Log.usr_log = logging.getLogger('usr_f')
        Log.auto_log = logging.getLogger('auto_f')
        Log.data_log = logging.getLogger('data_f')
        Log.request_log = logging.getLogger('requests_f')
        Log.order_log = logging.getLogger('order_f')

        # Configuration des handlers pour écrire dans différents fichiers
        usr_h = logging.FileHandler('logs/usr.log')
        auto_h = logging.FileHandler('logs/auto.log')
        data_h = logging.FileHandler('logs/data.log')
        request_h = logging.FileHandler('logs/request.log')
        order_h = logging.FileHandler('logs/order.log')

        # Définition des formats de logs
        formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
        usr_h.setFormatter(formatter)
        auto_h.setFormatter(formatter)
        data_h.setFormatter(formatter)
        request_h.setFormatter(formatter)
        order_h.setFormatter(formatter)

        # Ajouter les handlers aux loggers seulement s'ils ne sont pas déjà ajoutés
        if not Log.usr_log.handlers:
            Log.usr_log.addHandler(usr_h)
        if not Log.auto_log.handlers:
            Log.auto_log.addHandler(auto_h)
        if not Log.data_log.handlers:
            Log.data_log.addHandler(data_h)
        if not Log.request_log.handlers:
            Log.request_log.addHandler(request_h)
        if not Log.order_log.handlers:
            Log.order_log.addHandler(order_h)

    @staticmethod
    def usr(msg):
        Log.usr_log.info(msg) # type: ignore

    @staticmethod
    def auto(msg):
        Log.auto_log.info(msg) # type: ignore

    @staticmethod
    def data(msg):
        Log.data_log.info(msg) # type: ignore

    @staticmethod
    def request(msg):
        Log.request_log.info(msg) # type: ignore

    @staticmethod
    def order(msg):
        Log.order_log.info(msg) # type: ignore
