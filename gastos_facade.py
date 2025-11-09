from db_manager import db_manager
import threading
from datetime import datetime

class GastosFacade:
    
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
            
            con.commit()
            return True
        except Exception as err:
            if con: con.rollback()
            print(f"Error en Facade: {err}")
            return None
        finally:
            if cursor: cursor.close()
            if con: db_manager.close_connection(con)

    def find_user_by_credentials(self, username, password):
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        return self._execute_query(sql, (username, password), fetch_one=True, dictionary=True)

    def find_user_by_username(self, username):
        sql = "SELECT idUsuario FROM usuarios WHERE username = %s"
        return self._execute_query(sql, (username,), fetch_one=True)

    def create_user(self, username, password):
        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        return self._execute_query(sql, (username, password))

    def get_username_by_id(self, user_id):
        sql = "SELECT username FROM usuarios WHERE idUsuario = %s"
        result = self._execute_query(sql, (user_id,), fetch_one=True, dictionary=True)
        return result['username'] if result else "Usuario"

    def get_gastos_for_tbody(self, user_id):
        sql = """
            SELECT idGasto AS id, descripcion, monto, categoria, fecha 
            FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        return self._execute_query(sql, (user_id,), fetch_all=True, dictionary=True)

    def get_gastos_for_json(self, user_id):
        sql = "SELECT idGasto AS id, descripcion, monto, categoria, fecha FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC"
        gastos_db = self._execute_query(sql, (user_id,), fetch_all=True, dictionary=True)
        
        if gastos_db is None:
            return None
            
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
        sql = "INSERT INTO gastos (descripcion, monto, categoria, fecha, idUsuario) VALUES (%s, %s, %s, %s, %s)"
        params = (descripcion, float(monto), categoria, fecha, user_id)
        return self._execute_query(sql, params)

    def delete_gasto(self, gasto_id, user_id):
        sql = "DELETE FROM gastos WHERE idGasto = %s AND idUsuario = %s"
        return self._execute_query(sql, (gasto_id, user_id))

gastos_facade = GastosFacade.get_instance()
