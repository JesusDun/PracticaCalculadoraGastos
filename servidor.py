# Archivo: servidor.py
from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import pusher
import mysql.connector
from decimal import Decimal # Importante para la conversión
from datetime import date   # Importante para la conversión

# --- Configuración de la Aplicación ---
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

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

@app.route("/calculadora")
def calculadora():
    return render_template("calculadora.html")

# =========================================================================
# API PARA LA LÓGICA DE LA APLICACIÓN (CONECTADA A MYSQL)
# =========================================================================

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        sql = "SELECT * FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(sql, (usuario, password))
        if cursor.fetchone():
            return make_response(jsonify({"status": "success"}), 200)
        else:
            return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/tbodyGastos")
def tbodyGastos():
    try:
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        sql = """
            SELECT 
                idGasto AS id, 
                descripcion AS description, 
                monto AS amount, 
                categoria AS category, 
                fecha AS date 
            FROM gastos 
            ORDER BY idGasto DESC
        """
        cursor.execute(sql)
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
    try:
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        sql = """
            SELECT 
                idGasto AS id, 
                descripcion AS description, 
                monto AS amount, 
                categoria AS category, 
                fecha AS date 
            FROM gastos 
            ORDER BY idGasto DESC
        """
        cursor.execute(sql)
        gastos_desde_db = cursor.fetchall()
        
        # --- ESTA ES LA CORRECCIÓN CLAVE ---
        # Creamos una nueva lista "limpia" que jsonify sí puede entender
        gastos_limpios = []
        for gasto in gastos_desde_db:
            gasto_limpio = {}
            for key, value in gasto.items():
                if isinstance(value, Decimal):
                    # Si el valor es Decimal (dinero), lo convertimos a float
                    gasto_limpio[key] = float(value)
                elif isinstance(value, date):
                    # Si el valor es una fecha, lo convertimos a string
                    gasto_limpio[key] = value.strftime('%Y-%m-%d')
                else:
                    gasto_limpio[key] = value
            gastos_limpios.append(gasto_limpio)
            
        return jsonify(gastos_limpios)
        
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    try:
        id_usuario_actual = 1
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        sql = """
            INSERT INTO gastos (descripcion, monto, categoria, fecha, idUsuario) 
            VALUES (%s, %s, %s, %s, %s)
        """
        val = (
            request.form.get("description"),
            float(request.form.get("amount")),
            request.form.get("category"),
            request.form.get("date"),
            id_usuario_actual
        )
        cursor.execute(sql, val)
        con.commit()
        notificar_actualizacion_gastos()
        return make_response(jsonify({"status": "success"}), 201)
    except mysql.connector.Error as err:
        if 'con' in locals() and con.is_connected():
            con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    try:
        id_a_eliminar = int(request.form.get("id"))
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        sql = "DELETE FROM gastos WHERE idGasto = %s"
        cursor.execute(sql, (id_a_eliminar,))
        con.commit()
        notificar_actualizacion_gastos()
        return make_response(jsonify({"status": "success"}), 200)
    except mysql.connector.Error as err:
        if 'con' in locals() and con.is_connected():
            con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
