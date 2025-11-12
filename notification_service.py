from abc import ABC, abstractmethod
import pusher

# ---------------------------------------------
# Interfaz del Patrón Observer
# ---------------------------------------------
class Observer(ABC):
    @abstractmethod
    def update(self, event_type: str, data: any):
        pass

class Subject:
    def __init__(self):
        self._observers: list[Observer] = []

    def subscribe(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: Observer):
        self._observers.remove(observer)

    def notify(self, event_type: str, data: any):
        for observer in self._observers:
            observer.update(event_type, data)

# ---------------------------------------------
# Implementaciones Concretas
# ---------------------------------------------

class NotificationService(Subject):
    pass

class PusherObserver(Observer):
    def __init__(self):
        try:
            self.pusher_client = pusher.Pusher(
                app_id='2050408',
                key='b338714caa5dd2af623d',
                secret='145fd82f4c76138cfdbd',
                cluster='us2',
                ssl=True
            )
        except Exception as e:
            print(f"Error inicializando Pusher: {e}")
            self.pusher_client = None

    def update(self, event_type: str, data: any):
        if not self.pusher_client:
            print("Pusher no está inicializado.")
            return

        if event_type == "GASTO_AGREGADO" or event_type == "GASTO_ELIMINADO":
            try:
                self.pusher_client.trigger('canal-gastos', 'evento-actualizacion', {'message': 'actualizar'})
            except Exception as e:
                print(f"Error al notificar a Pusher: {e}")

class LoggingObserver(Observer):
    def update(self, event_type: str, data: any):
        if event_type == "GASTO_AGREGADO":
            print(f"[LOG] Gasto Agregado: Usuario {data['user_id']}, Monto {data['monto']}")
        elif event_type == "GASTO_ELIMINADO":
            print(f"[LOG] Gasto Eliminado: ID {data['gasto_id']} por Usuario {data['user_id']}")
        elif event_type == "USUARIO_REGISTRADO":
            print(f"[LOG] Usuario Registrado: {data['username']}")

# ---------------------------------------------
# Instancia Singleton del Subject (Servicio)
# ---------------------------------------------
notification_service = NotificationService()
