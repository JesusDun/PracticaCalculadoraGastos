import os
import logging
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from app_mediator import app_mediator
from daos import LogDAO 

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

# --- CONFIGURACIÓN SEGURA DE AUDITORÍA Y MONITOREO ---
RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_LOG = os.path.join(RUTA_BASE, 'registro_eventos.log')

# --- MI HORA LOCAL ---
ZONA_LOCAL = timezone(timedelta(hours=-6))

logging.Formatter.converter = lambda *args: datetime.now(ZONA_LOCAL).timetuple()

logging.basicConfig(
    filename=RUTA_LOG,
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

log_dao = LogDAO()

with app.app_context():
    try:
        log_dao.create_table()
    except Exception as e:
        print(f"Advertencia al crear tabla de logs: {e}")

def registrar_auditoria(usuario, accion, nivel):
    fecha_local = datetime.now(ZONA_LOCAL).strftime('%Y-%m-%d %H:%M:%S')
    try:
        log_dao.registrar_evento(usuario, accion, nivel, fecha_local)
    except Exception as e:
        print(f"Error guardando log en BD: {e}")
        
    mensaje = f"Usuario: {usuario} | Acción: {accion} | Nivel: {nivel}"
    if nivel == 'Ataque':
        logging.warning(mensaje)
    elif nivel == 'Aviso':
        logging.info(mensaje)
    else: 
        logging.debug(mensaje)

# --- RUTAS DE LA APLICACIÓN ---

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/registro")
def registro():
    return render_template("registro.html")

@app.route("/calculadora")
def calculadora():
    if 'idUsuario' not in session:
        return redirect(url_for('login'))
    try:
        username = app_mediator.get_username(session['idUsuario'])
        hora_actual = datetime.now().hour
        if 5 <= hora_actual < 12: saludo = "Buenos Días"
        elif 12 <= hora_actual < 20: saludo = "Buenas Tardes"
        else: saludo = "Buenas Noches"
        return render_template("calculadora.html", saludo=saludo, username=username)
    except Exception as err:
        print(f"Error en /calculadora: {err}")
        return render_template("calculadora.html", saludo="Bienvenido", username="Usuario")

@app.route("/registrarUsuario", methods=["POST"])
def registrarUsuario():
    usuario_intento = request.form.get('txtUsuario', 'Desconocido')
    response, code = app_mediator.registrar_usuario(request.form)
    
    if code in [200, 201]:
        registrar_auditoria(usuario_intento, "Registro de usuario exitoso", "Movimiento")
    else:
        registrar_auditoria(usuario_intento, "Fallo al registrar usuario", "Aviso")
        
    return make_response(jsonify(response), code)

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    usuario_intento = request.form.get('txtUsuario', 'Desconocido')
    response, code = app_mediator.iniciar_sesion(request.form)
    
    if code == 200:
        session['idUsuario'] = response["user_id"]
        session['username'] = usuario_intento
        registrar_auditoria(usuario_intento, "Inicio de sesión exitoso", "Movimiento")
    else:
        registrar_auditoria(usuario_intento, "Intento de inicio de sesión fallido", "Ataque")
        
    return make_response(jsonify(response), code)

@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    usuario = session.get('username', 'Usuario Desconocido')
    session.clear()
    registrar_auditoria(usuario, "Cierre de sesión", "Movimiento")
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

@app.route("/tbodyGastos")
def tbodyGastos():
    if 'idUsuario' not in session: 
        return "<tr><td colspan='4'>Acceso no autorizado</td></tr>"
    try:
        gastos = app_mediator.get_tbody_gastos(session['idUsuario'])
        return render_template("tbodyGastos.html", gastos=gastos)
    except Exception as err:
        return f"<tr><td colspan='4'>Error al cargar datos: {err}</td></tr>"

@app.route("/gastos/json")
def gastos_json():
    if 'idUsuario' not in session: 
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    gastos = app_mediator.get_json_gastos(session['idUsuario'])
    if gastos is None:
         return make_response(jsonify({"error": "Error al obtener gastos"}), 500)
    return jsonify(gastos)

@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    if 'idUsuario' not in session: 
        registrar_auditoria("Desconocido", "Intento de crear gasto sin sesión", "Ataque")
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    
    usuario = session.get('username', f"ID: {session['idUsuario']}")
    response, code = app_mediator.agregar_gasto(session['idUsuario'], request.form)
    
    if code in [200, 201]:
        registrar_auditoria(usuario, "Agregó un nuevo gasto", "Movimiento")
        
    return make_response(jsonify(response), code)

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    if 'idUsuario' not in session: 
        registrar_auditoria("Desconocido", "Intento de eliminar gasto sin sesión", "Ataque")
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    usuario = session.get('username', f"ID: {session['idUsuario']}")
    response, code = app_mediator.eliminar_gasto(session['idUsuario'], request.form)
    
    if code == 200:
        registrar_auditoria(usuario, "Eliminó un gasto", "Aviso")
        
    return make_response(jsonify(response), code)

@app.route("/exportar/<tipo>")
def exportar_gastos(tipo):
    if 'idUsuario' not in session:
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    try:
        reporte_decorado = app_mediator.generar_reporte(session['idUsuario'], tipo)
        if isinstance(reporte_decorado, dict):
            return make_response(jsonify(reporte_decorado), 500)
        contenido = reporte_decorado.generar_reporte()
        response = make_response(contenido)
        response.headers['Content-Disposition'] = f'attachment; filename={reporte_decorado.get_filename()}'
        response.headers['Content-Type'] = reporte_decorado.get_mimetype()
        return response
    except Exception as e:
        return make_response(jsonify({"error": f"Error: {e}"}), 500)

@app.route('/monitoreo_logs')
def monitoreo_logs():
    if 'idUsuario' not in session:
        registrar_auditoria("Desconocido", "Intento de acceder a logs sin sesión", "Ataque")
        return redirect(url_for('login'))
    
    usuario = session.get('username', 'Usuario')
    registrar_auditoria(usuario, "Visualizó el panel de monitoreo", "Aviso")
        
    logs_db = log_dao.obtener_logs()
    
    try:
        with open(RUTA_LOG, 'r') as f:
            lineas = f.readlines()
            logs_archivo = list(reversed(lineas[-5:]))
    except FileNotFoundError:
        logs_archivo = []

    return render_template('logs.html', logs_db=logs_db, logs_archivo=logs_archivo)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
