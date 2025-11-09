# gastos_facade.py
from db_manager import db_manager # Importamos el Singleton de conexión
import threading

class GastosFacade:
    """
    Implementación del patrón Facade (y Singleton) para
    centralizar y simplificar todo el acceso a la base de datos.
    El servidor ya no escribirá SQL, solo llamará a estos métodos.
    """
    
    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def get_instance():
        if GastosFacade._instance is None:
            with GastosFacade._lock:
                if GastosFacade._instance is None:
                    GastosFacade._instance = GastosFacade()
        return GastosFacade._instance

    def _execute_query(self, query, params=None, fetch_one=False, fetch_all=False, dictionary=False):
        """Método helper privado para manejar conexiones y cursores."""
        con = None
        cursor = None
        try:
            con = db_manager.get_connection()
            if not con:
                raise Exception("No se pudo obtener conexión del pool")
            
            cursor = con.cursor(dictionary=dictionary)
            cursor.execute(query, params or ())
            
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            
            con.commit() # Asumimos commit para operaciones que no son 'fetch'
            return True
        except Exception as err:
            if con: con.rollback()
            print(f"Error en Facade: {err}")
            return None
        finally:
            if cursor: cursor.close()
            if con: db_manager.close_connection(con)

    # --- Métodos de la Fachada (API Simplificada) ---

    def find_user_by_credentials(self, username, password):
        """Encuentra un usuario por username y password. Usado en /iniciarSesion."""
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        return self._execute_query(sql, (username, password), fetch_one=True, dictionary=True)

    def find_user_by_username(self, username):
        """Verifica si un username ya existe. Usado en /registrarUsuario."""
        sql = "SELECT idUsuario FROM usuarios WHERE username = %s"
        return self._execute_query(sql, (username,), fetch_one=True)

    def create_user(self, username, password):
        """Crea un nuevo usuario. Usado en /registrarUsuario."""
        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        return self._execute_query(sql, (username, password))

    def get_username_by_id(self, user_id):
        """Obtiene el username de un usuario. Usado en /calculadora."""
        sql = "SELECT username FROM usuarios WHERE idUsuario = %s"
        result = self._execute_query(sql, (user_id,), fetch_one=True, dictionary=True)
        return result['username'] if result else "Usuario"

    def get_gastos_for_tbody(self, user_id):
        """Obtiene los gastos para la tabla HTML. Usado en /tbodyGastos."""
        sql = """
            SELECT idGasto AS id, descripcion, monto, categoria, fecha 
            FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        return self._execute_query(sql, (user_id,), fetch_all=True, dictionary=True)

    def get_gastos_for_json(self, user_id):
        """Obtiene los gastos para el JSON. Usado en /gastos/json y /exportar."""
        sql = "SELECT idGasto AS id, descripcion, monto, categoria, fecha FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC"
        gastos_db = self._execute_query(sql, (user_id,), fetch_all=True, dictionary=True)
        
        if gastos_db is None:
            return None
            
        # Procesamos los datos como lo hacíamos antes
        gastos_limpios = []
        for gasto in gastos_db:
            gastos_limpios.append({
                'id': gasto['id'],
                'descripcion': gasto['descripcion'],
                'monto': float(gasto['monto']),
                'categoria': gasto['categoria'],
                'fecha': gasto['fecha'].strftime('%Y-%m-%d')
            })
        return gastos_limpios

    def add_gasto(self, user_id, descripcion, monto, categoria, fecha):
        """Agrega un nuevo gasto. Usado en /gasto."""
        sql = "INSERT INTO gastos (descripcion, monto, categoria, fecha, idUsuario) VALUES (%s, %s, %s, %s, %s)"
        params = (descripcion, float(monto), categoria, fecha, user_id)
        return self._execute_query(sql, params)

    def delete_gasto(self, gasto_id, user_id):
        """Elimina un gasto. Usado en /gasto/eliminar."""
        sql = "DELETE FROM gastos WHERE idGasto = %s AND idUsuario = %s"
        return self._execute_query(sql, (gasto_id, user_id))

# Instancia global única de la fachada (Singleton)
gastos_facade = GastosFacade.get_instance()
