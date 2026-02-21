from db_manager import db_manager

class BaseDAO:
    def _execute(self, query, params=None, fetch_one=False, fetch_all=False, dictionary=False):
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
            print(f"Error en DAO: {err}")
            return None
        finally:
            if cursor: cursor.close()
            if con: db_manager.close_connection(con)

class UsuarioDAO(BaseDAO):
    
    def get_by_credentials(self, username, password):
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        return self._execute(sql, (username, password), fetch_one=True, dictionary=True)

    def get_by_username(self, username):
        sql = "SELECT idUsuario FROM usuarios WHERE username = %s"
        return self._execute(sql, (username,), fetch_one=True)

    def create(self, username, password):
        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        return self._execute(sql, (username, password))

    def get_username_by_id(self, user_id):
        sql = "SELECT username FROM usuarios WHERE idUsuario = %s"
        result = self._execute(sql, (user_id,), fetch_one=True, dictionary=True)
        return result['username'] if result else "Usuario"

class GastoDAO(BaseDAO):

    def get_all_by_user(self, user_id):
        sql = """
            SELECT idGasto AS id, descripcion, monto, categoria, fecha 
            FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        return self._execute(sql, (user_id,), fetch_all=True, dictionary=True)

    def create(self, user_id, descripcion, monto, categoria, fecha):
        sql = "INSERT INTO gastos (descripcion, monto, categoria, fecha, idUsuario) VALUES (%s, %s, %s, %s, %s)"
        params = (descripcion, float(monto), categoria, fecha, user_id)
        return self._execute(sql, params)

    def delete(self, gasto_id, user_id):
        sql = "DELETE FROM gastos WHERE idGasto = %s AND idUsuario = %s"
        return self._execute(sql, (gasto_id, user_id))

class LogDAO(BaseDAO):
    def create_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS bitacora_eventos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario VARCHAR(255),
            accion TEXT,
            nivel VARCHAR(50),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        return self._execute(sql)

    def registrar_evento(self, usuario, accion, nivel, fecha_local):
        sql = "INSERT INTO bitacora_eventos (usuario, accion, nivel, fecha) VALUES (%s, %s, %s, %s)"
        return self._execute(sql, (usuario, accion, nivel, fecha_local))

    def obtener_logs(self):
        sql = "SELECT usuario, accion, nivel, fecha FROM bitacora_eventos ORDER BY fecha DESC LIMIT 5"
        return self._execute(sql, fetch_all=True, dictionary=True)
