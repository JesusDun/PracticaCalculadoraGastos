# Archivo: servidor.py
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
import pusher
import mysql.connector
from decimal import Decimal
from datetime import date
from datetime import datetime

# --- Configuración de la Aplicación ---
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
# NUEVO: Se necesita una "llave secreta" para manejar las sesiones de forma segura.
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

# --- Configuración de Pusher ---
pusher_client = pusher.Pusher(
    app_id='2050408',
    key='b338714caa5dd2af623d',
    secret='145fd82f4c76138cfdbd',
    cluster='us2',
    ssl=True
)

# --- Configuración de la base de datos ---
db_config = {
    "host": "185.232.14.52",
    "database": "u760464709_23005283_bd",
    "user": "u760464709_23005283_usr",
    "password": "rnUxcf3P#a"
}

def notificar_actualizacion_gastos():
    pusher_client.trigger('canal-gastos', 'evento-actualizacion', {'message': 'actualizar'})

# =========================================================================
# RUTAS PARA SERVIR LAS PÁGINAS HTML
# =========================================================================

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/registro")
def registro():
    return render_template("registro.html")

@app.route("/calculadora")
def calculadora():
    # Protegemos la ruta. Si no hay sesión, se redirige al login.
    if 'idUsuario' not in session:
        return redirect(url_for('login'))

    # --- LÓGICA DEL SALUDO DINÁMICO ---
    try:
        id_usuario_actual = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT username FROM usuarios WHERE idUsuario = %s", (id_usuario_actual,))
        usuario = cursor.fetchone()
        username = usuario['username'] if usuario else "Usuario"

        hora_actual = datetime.now().hour
        saludo = "Buenas Noches"
        if 5 <= hora_actual < 12:
            saludo = "Buenos Días"
        elif 12 <= hora_actual < 20:
            saludo = "Buenas Tardes"

        return render_template("calculadora.html", saludo=saludo, username=username)

    except mysql.connector.Error as err:
        return render_template("calculadora.html", saludo="Bienvenido", username="Usuario")
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

# =========================================================================
# API PARA LA LÓGICA DE LA APLICACIÓN
# =========================================================================

# NUEVA RUTA: Para registrar un nuevo usuario
@app.route("/registrarUsuario", methods=["POST"])
def registrarUsuario():
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()

        # Primero, verificamos si el usuario ya existe
        cursor.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (usuario,))
        if cursor.fetchone():
            return make_response(jsonify({"error": "El nombre de usuario ya está en uso."}), 409)

        # Si no existe, lo insertamos
        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (usuario, password))
        con.commit()
        return make_response(jsonify({"status": "Usuario registrado exitosamente"}), 201)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True) # dictionary=True para obtener el ID
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(sql, (usuario, password))
        user_data = cursor.fetchone()
        
        if user_data:
            # MODIFICADO: Guardamos el ID del usuario en la sesión
            session['idUsuario'] = user_data['idUsuario']
            return make_response(jsonify({"status": "success"}), 200)
        else:
            return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

# NUEVA RUTA: Para cerrar la sesión
@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    session.clear() # Limpia todos los datos de la sesión
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

# --- TODAS LAS RUTAS DE GASTOS AHORA USAN EL ID DE LA SESIÓN ---

@app.route("/tbodyGastos")
def tbodyGastos():
    if 'idUsuario' not in session: return "<tr><td colspan='4'>Acceso no autorizado</td></tr>"
    try:
        id_usuario_actual = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        sql = """
            SELECT idGasto AS id, descripcion AS description, monto AS amount, categoria AS category, fecha AS date 
            FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        cursor.execute(sql, (id_usuario_actual,))
        gastos_ordenados = cursor.fetchall()
        return render_template("tbodyGastos.html", gastos=gastos_ordenados)
    except mysql.connector.Error as err:
        return f"<tr><td colspan='4'>Error al cargar datos: {err}</td></tr>"
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/gastos/json")
def gastos_json():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    try:
        id_usuario_actual = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        sql = "SELECT idGasto AS id, descripcion, monto, categoria, fecha FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC"
        cursor.execute(sql, (id_usuario_actual,))
        gastos_desde_db = cursor.fetchall()
        
        gastos_limpios = []
        for gasto in gastos_desde_db:
            gastos_limpios.append({
                'id': gasto['id'],
                'description': gasto['descripcion'],
                'amount': float(gasto['monto']),
                'category': gasto['categoria'],
                'date': gasto['fecha'].strftime('%Y-%m-%d')
            })
        return jsonify(gastos_limpios)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    try:
        id_usuario_actual = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        sql = "INSERT INTO gastos (descripcion, monto, categoria, fecha, idUsuario) VALUES (%s, %s, %s, %s, %s)"
        val = (
            request.form.get("description"), float(request.form.get("amount")),
            request.form.get("category"), request.form.get("date"),
            id_usuario_actual
        )
        cursor.execute(sql, val)
        con.commit()
        notificar_actualizacion_gastos()
        return make_response(jsonify({"status": "success"}), 201)
    except mysql.connector.Error as err:
        if 'con' in locals() and con.is_connected(): con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    try:
        id_a_eliminar = int(request.form.get("id"))
        id_usuario_actual = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        # MODIFICADO: Solo se puede borrar un gasto si pertenece al usuario actual.
        sql = "DELETE FROM gastos WHERE idGasto = %s AND idUsuario = %s"
        cursor.execute(sql, (id_a_eliminar, id_usuario_actual))
        con.commit()
        notificar_actualizacion_gastos()
        return make_response(jsonify({"status": "success"}), 200)
    except mysql.connector.Error as err:
        if 'con' in locals() and con.is_connected(): con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
