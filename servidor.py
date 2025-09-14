# Archivo: servidor.py
from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import pusher
import mysql.connector

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

# --- Función para notificar a los clientes ---
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
    # 3. EJECUTAMOS LA LÓGICA DE LA BASE DE DATOS
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
        # dictionary=True nos permite acceder a los datos por nombre de columna
        cursor = con.cursor(dictionary=True)
        
        # Renombramos las columnas con AS para que coincidan con el HTML
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
        # En caso de error, devolvemos un HTML vacío con un mensaje
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
        
        # Formateamos la fecha para que JavaScript la entienda fácilmente
        sql = """
            SELECT 
                idGasto AS id, 
                descripcion AS description, 
                monto AS amount, 
                categoria AS category, 
                DATE_FORMAT(fecha, '%%Y-%%m-%%d') AS date 
            FROM gastos 
            ORDER BY idGasto DESC
        """
        cursor.execute(sql)
        gastos = cursor.fetchall()
        
        return jsonify(gastos)
        
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    try:
        # NOTA: Para una app real con múltiples usuarios, aquí obtendrías el ID del usuario de la sesión.
        # Por simplicidad, asumimos que todos los gastos son del usuario con id=1 ('admin').
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
        con.commit() # ¡Importante! Guarda los cambios en la base de datos.
        
        notificar_actualizacion_gastos()
        return make_response(jsonify({"status": "success"}), 201)

    except mysql.connector.Error as err:
        if 'con' in locals() and con.is_connected():
            con.rollback() # Revierte los cambios si hay un error
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

# --- Ejecutar el Servidor ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
