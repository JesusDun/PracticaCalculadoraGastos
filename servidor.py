import os
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import logging
from app_mediator import app_mediator
from daos import LogDAO 

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

# --- CONFIGURACIÓN SEGURA DE AUDITORÍA Y MONITOREO ---

# 1. Definimos una ruta absoluta para asegurar que el archivo de log se cree en la carpeta correcta
RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_LOG = os.path.join(RUTA_BASE, 'registro_eventos.log')

logging.basicConfig(
    filename=RUTA_LOG,
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 2. Inicializamos DAO globalmente, pero posponemos la creación de la tabla
log_dao = LogDAO()

# 3. Usamos el contexto de Flask para crear la tabla de forma segura sin bloquear la app
with app.app_context():
    try:
        log_dao.create_table()
    except Exception as e:
        print(f"Advertencia al crear tabla de logs: {e}")

def registrar_auditoria(usuario, accion, nivel):
    """Guarda el evento en Base de Datos y en el archivo log .txt."""
    try:
        log_dao.registrar_evento(usuario, accion, nivel)
    except Exception as e:
        print(f"Error guardando log en BD: {e}")
        
    mensaje = f"Usuario: {usuario} | Acción: {accion} | Nivel: {nivel}"
    
    if nivel == 'Ataque':
        logging.warning(mensaje)
    elif nivel == 'Aviso':
        logging.info(mensaje)
    else: # Movimiento
        logging.debug(mensaje)

# ... [AQUÍ MANTIENES TODAS TUS RUTAS (login, registro, calculadora, etc.) IGUAL QUE ANTES] ...

# --- MODIFICACIÓN DE LA RUTA PARA MOSTRAR LOGS ---
@app.route('/monitoreo_logs')
def monitoreo_logs():
    if 'idUsuario' not in session:
        registrar_auditoria("Desconocido", "Intento de acceder a panel de logs sin sesión", "Ataque")
        return redirect(url_for('login'))
    
    usuario = session.get('username', 'Usuario')
    registrar_auditoria(usuario, "Visualizó el panel de monitoreo de Logs", "Aviso")
        
    # Extraer logs de la DB
    logs_db = log_dao.obtener_logs()
    
    # Extraer logs del archivo .txt usando la ruta absoluta segura
    try:
        with open(RUTA_LOG, 'r') as f:
            logs_archivo = f.readlines()
    except FileNotFoundError:
        logs_archivo = ["El archivo log aún no ha sido creado."]

    return render_template('logs.html', logs_db=logs_db, logs_archivo=logs_archivo)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
