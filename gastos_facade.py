import threading
from daos import UsuarioDAO, GastoDAO

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

    def __init__(self):
        self.usuario_dao = UsuarioDAO()
        self.gasto_dao = GastoDAO()

    def find_user_by_credentials(self, username, password):
        return self.usuario_dao.get_by_credentials(username, password)

    def find_user_by_username(self, username):
        return self.usuario_dao.get_by_username(username)

    def create_user(self, username, password):
        return self.usuario_dao.create(username, password)

    def get_username_by_id(self, user_id):
        return self.usuario_dao.get_username_by_id(user_id)

    def get_gastos_for_tbody(self, user_id):
        return self.gasto_dao.get_all_by_user(user_id)

    def get_gastos_for_json(self, user_id):
        gastos_db = self.gasto_dao.get_all_by_user(user_id)
        
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
        return self.gasto_dao.create(user_id, descripcion, monto, categoria, fecha)

    def delete_gasto(self, gasto_id, user_id):
        return self.gasto_dao.delete(gasto_id, user_id)

gastos_facade = GastosFacade.get_instance()
