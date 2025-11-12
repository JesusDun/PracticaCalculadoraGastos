import threading
from gastos_facade import gastos_facade
from report_factory import ReportFactory, ReporteConEncabezado
from notification_service import notification_service, PusherObserver, LoggingObserver

class AppMediator:
    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def get_instance():
        if AppMediator._instance is None:
            with AppMediator._lock:
                if AppMediator._instance is None:
                    AppMediator._instance = AppMediator()
        return AppMediator._instance

    def __init__(self):
        if AppMediator._instance is not None:
            raise Exception("Esta clase es un Singleton. Usa get_instance().")
        
        self.facade = gastos_facade
        self.report_factory = ReportFactory()
        self.notifier = notification_service
        
        self._setup_observers()

    def _setup_observers(self):
        self.notifier.subscribe(PusherObserver())
        self.notifier.subscribe(LoggingObserver())

    def registrar_usuario(self, form_data):
        username = form_data.get("txtUsuario")
        password = form_data.get("txtContrasena")
        
        if self.facade.find_user_by_username(username):
            return {"error": "El nombre de usuario ya está en uso."}, 409
        
        if self.facade.create_user(username, password):
            self.notifier.notify("USUARIO_REGISTRADO", {"username": username})
            return {"status": "Usuario registrado exitosamente"}, 201
        
        return {"error": "Error de base de datos"}, 500

    def iniciar_sesion(self, form_data):
        username = form_data.get("txtUsuario")
        password = form_data.get("txtContrasena")
        
        user_data = self.facade.find_user_by_credentials(username, password)
        
        if user_data:
            return {"status": "success", "user_id": user_data['idUsuario']}, 200
        
        return {"error": "Usuario o contraseña incorrectos"}, 401

    def get_username(self, user_id):
        return self.facade.get_username_by_id(user_id)

    def get_tbody_gastos(self, user_id):
        return self.facade.get_gastos_for_tbody(user_id)

    def get_json_gastos(self, user_id):
        return self.facade.get_gastos_for_json(user_id)

    def agregar_gasto(self, user_id, form_data):
        try:
            monto = float(form_data.get("monto"))
            datos_gasto = {
                "user_id": user_id,
                "descripcion": form_data.get("descripcion"),
                "monto": monto,
                "categoria": form_data.get("categoria"),
                "fecha": form_data.get("fecha")
            }

            if self.facade.add_gasto(**datos_gasto):
                self.notifier.notify("GASTO_AGREGADO", datos_gasto)
                return {"status": "success"}, 201
            
            return {"error": "Error al agregar gasto"}, 500
            
        except Exception as e:
            print(f"Error en mediador (agregar_gasto): {e}")
            return {"error": f"Error de datos: {e}"}, 500

    def eliminar_gasto(self, user_id, form_data):
        try:
            gasto_id = int(form_data.get("id"))
            
            if self.facade.delete_gasto(gasto_id, user_id):
                self.notifier.notify("GASTO_ELIMINADO", {"gasto_id": gasto_id, "user_id": user_id})
                return {"status": "success"}, 200
            
            return {"error": "Error al eliminar gasto"}, 500

        except Exception as e:
            print(f"Error en mediador (eliminar_gasto): {e}")
            return {"error": f"Error de datos: {e}"}, 500

    def generar_reporte(self, user_id, tipo_reporte):
        gastos = self.facade.get_gastos_for_json(user_id)
        if gastos is None:
            return {"error": "No se pudieron obtener los datos"}, 500
        
        username = self.facade.get_username_by_id(user_id)
        
        reporte_base = self.report_factory.crear_reporte(tipo_reporte, gastos)
        reporte_decorado = ReporteConEncabezado(reporte_base, username)
        
        return reporte_decorado

app_mediator = AppMediator.get_instance()
