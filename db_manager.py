import mysql.connector
import threading

db_config = {
    "host": "185.232.14.52",
    "database": "u760464709_23005283_bd",
    "user": "u760464709_23005283_usr",
    "password": "rnUxcf3P#a",
    "pool_name": "mypool",
    "pool_size": 5
}

class DatabaseManager:
    
    _instance = None
    
    _lock = threading.Lock()

    def __init__(self):
        if DatabaseManager._instance is not None:
            raise Exception("Esta clase es un Singleton. Usa el método get_instance().")
        else:
            try:
                self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
                print("Pool de conexiones de BD (Singleton) creado exitosamente.")
            except mysql.connector.Error as err:
                print(f"Error al crear el pool de conexiones: {err}")
                self.connection_pool = None

    @staticmethod
    def get_instance():
        if DatabaseManager._instance is None:
            with DatabaseManager._lock:
                if DatabaseManager._instance is None:
                    DatabaseManager._instance = DatabaseManager()
        return DatabaseManager._instance

    def get_connection(self):
        if self.connection_pool:
            try:
                return self.connection_pool.get_connection()
            except mysql.connector.Error as err:
                print(f"Error al obtener conexión del pool: {err}")
                return None
        else:
            print("Error: El pool de conexiones no está inicializado.")
            return None

    def close_connection(self, connection):
        if connection:
            try:
                connection.close()
            except mysql.connector.Error as err:
                print(f"Error al devolver conexión al pool: {err}")


try:
    db_manager = DatabaseManager.get_instance()
except Exception as e:
    print(f"Error inicializando el Singleton de BD: {e}")
    db_manager = None
