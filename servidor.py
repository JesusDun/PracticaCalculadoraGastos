from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import logging
from app_mediator import app_mediator
from daos import LogDAO # Se importa el DAO recién creado

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

# --- CONFIGURACIÓN DE AUDITORÍA Y MONITOREO ---
logging.basicConfig(
    filename='registro_eventos.log',
    level=logging.DEBUG, # Usar DEBUG para poder registrar los "Movimientos"
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Se inicializa la tabla de bitácora en la Base de Datos
log_dao = LogDAO()
log_dao.create_table()

def registrar_auditoria(usuario, accion, nivel):
    """Guarda el evento en Base de Datos y en el archivo log .txt."""
    log_dao.registrar_evento(usuario, accion, nivel)
    mensaje = f"Usuario: {usuario} | Acción: {accion} | Nivel: {nivel}"
    
    if nivel == 'Ataque':
        logging.warning(mensaje)
    elif nivel == 'Aviso':
        logging.info(mensaje)
    else: # Movimiento
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
    usuario_intento = request.form.get('username', 'Desconocido')
    response, code = app_mediator.registrar_usuario(request.form)
    
    if code in [200, 201]:
        registrar_auditoria(usuario_intento, "Registro de nuevo usuario exitoso", "Movimiento")
    else:
        registrar_auditoria(usuario_intento, f"Fallo al registrar usuario: {response.get('error','')}", "Aviso")
        
    return make_response(jsonify(response), code)

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    usuario_intento = request.form.get('username', 'Desconocido')
    response, code = app_mediator.iniciar_sesion(request.form)
    
    if code == 200:
        session['idUsuario'] = response["user_id"]
        session['username'] = usuario_intento # Se guarda en sesión para logs
        registrar_auditoria(usuario_intento, "Inicio de sesión exitoso", "Movimiento")
    else:
        registrar_auditoria(usuario_intento, "Intento de inicio de sesión fallido con credenciales inválidas", "Ataque")
        
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
        registrar_auditoria("Desconocido", "Intento de acceder a gastos sin sesión", "Ataque")
        return "<tr><td colspan='4'>Acceso no autorizado</td></tr>"
    try:
        gastos = app_mediator.get_tbody_gastos(session['idUsuario'])
        return render_template("tbodyGastos.html", gastos=gastos)
    except Exception as err:
        print(f"Error en /tbodyGastos: {err}")
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
        registrar_auditoria("Desconocido", "Intento de crear gasto por API sin sesión", "Ataque")
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    
    usuario = session.get('username', f"ID: {session['idUsuario']}")
    response, code = app_mediator.agregar_gasto(session['idUsuario'], request.form)
    
    if code in [200, 201]:
        registrar_auditoria(usuario, "Agregó un nuevo gasto", "Movimiento")
        
    return make_response(jsonify(response), code)

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    if 'idUsuario' not in session: 
        registrar_auditoria("Desconocido", "Intento de eliminar gasto por API sin sesión", "Ataque")
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    usuario = session.get('username', f"ID: {session['idUsuario']}")
    response, code = app_mediator.eliminar_gasto(session['idUsuario'], request.form)
    
    if code == 200:
        registrar_auditoria(usuario, "Eliminó un gasto del sistema", "Aviso")
        
    return make_response(jsonify(response), code)

@app.route("/exportar/<tipo>")
def exportar_gastos(tipo):
    if 'idUsuario' not in session:
        registrar_auditoria("Desconocido", f"Intento de exportar reporte {tipo} sin sesión", "Ataque")
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    usuario = session.get('username', f"ID: {session['idUsuario']}")

    try:
        reporte_decorado = app_mediator.generar_reporte(session['idUsuario'], tipo)
        
        if isinstance(reporte_decorado, dict):
            return make_response(jsonify(reporte_decorado), 500)

        contenido = reporte_decorado.generar_reporte()
        
        response = make_response(contenido)
        response.headers['Content-Disposition'] = f'attachment; filename={reporte_decorado.get_filename()}'
        response.headers['Content-Type'] = reporte_decorado.get_mimetype()
        
        registrar_auditoria(usuario, f"Exportó un reporte de gastos en formato {tipo}", "Movimiento")
        return response

    except ValueError as ve:
        return make_response(jsonify({"error": str(ve)}), 400)
    except Exception as e:
        print(f"Error en /exportar: {e}")
        return make_response(jsonify({"error": f"Error interno del servidor: {e}"}), 500)

# --- NUEVA RUTA PARA MOSTRAR LOGS ---
@app.route('/monitoreo_logs')
def monitoreo_logs():
    if 'idUsuario' not in session:
        registrar_auditoria("Desconocido", "Intento de acceder a panel de logs sin sesión", "Ataque")
        return redirect(url_for('login'))
    
    usuario = session.get('username', 'Usuario')
    registrar_auditoria(usuario, "Visualizó el panel de monitoreo de Logs", "Aviso")
        
    # Extraer logs de la DB
    logs_db = log_dao.obtener_logs()
    
    # Extraer logs del archivo .txt
    try:
        with open('registro_eventos.log', 'r') as f:
            logs_archivo = f.readlines()
    except FileNotFoundError:
        logs_archivo = ["El archivo log aún no ha sido creado."]

    return render_template('logs.html', logs_db=logs_db, logs_archivo=logs_archivo)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
