# Archivo: servidor.py
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
import pusher
# import mysql.connector   # <--- 1. Ya no utilizaré mysql.connector directamente
from decimal import Decimal
from datetime import date
from datetime import datetime
from report_factory import ReportFactory
from db_manager import db_manager

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
    if 'idUsuario' not in session:
        return redirect(url_for('login'))

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']

        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT username FROM usuarios WHERE idUsuario = %s", (id_usuario_actual,))
        usuario = cursor.fetchone()
        username = usuario['username'] if usuario else "Usuario"

    # --- LÓGICA DEL SALUDO DINÁMICO ---
        hora_actual = datetime.now().hour
        
        if 5 <= hora_actual < 12:
            saludo = "Buenos Días"
        elif 12 <= hora_actual < 20: # De 12 PM a 7:59 PM
            saludo = "Buenas Tardes"
        else: # Para el resto de las horas (noche y madrugada)
            saludo = "Buenas Noches"

        return render_template("calculadora.html", saludo=saludo, username=username)

    except Exception as err:
        print(f"Error en /calculadora: {err}")
        return render_template("calculadora.html", saludo="Bienvenido", username="Usuario")
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# API PARA LA LÓGICA DE LA APLICACIÓN
# =========================================================================

# NUEVA RUTA: Para registrar un nuevo usuario
@app.route("/registrarUsuario", methods=["POST"])
def registrarUsuario():

    con = None
    cursor = None
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor()
        cursor.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (usuario,))
        if cursor.fetchone():
            return make_response(jsonify({"error": "El nombre de usuario ya está en uso."}), 409)

        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (usuario, password))
        con.commit()
        return make_response(jsonify({"status": "Usuario registrado exitosamente"}), 201)
    except mysql.connector.Error as err:
        print(f"Error en /registrarUsuario: {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    con = None
    cursor = None
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(sql, (usuario, password))
        user_data = cursor.fetchone()
        
        if user_data:
            session['idUsuario'] = user_data['idUsuario']
            return make_response(jsonify({"status": "success"}), 200)
        else:
            return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)
    except Exception as err:
        print(f"Error en /iniciarSesion: {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    session.clear()
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

# --- TODAS LAS RUTAS DE GASTOS AHORA USAN EL ID DE LA SESIÓN ---

# --- Función para Obtener Gastos ---
def get_gastos_usuario(id_usuario_actual):
    con = None
    cursor = None
    try:
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
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
        return gastos_limpios
    except Exception as err:
        print(f"Error en get_gastos_usuario: {err}")
        return None
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)
# --- FIN DE FUNCIÓN AUXILIAR ---

@app.route("/tbodyGastos")
def tbodyGastos():
    if 'idUsuario' not in session: return "<tr><td colspan='4'>Acceso no autorizado</td></tr>"

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        sql = """
            SELECT idGasto AS id, descripcion AS description, monto AS amount, categoria AS category, fecha AS date 
            FROM gastos WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        cursor.execute(sql, (id_usuario_actual,))
        gastos_ordenados = cursor.fetchall()
        return render_template("tbodyGastos.html", gastos=gastos_ordenados)
    except Exception as err:
        print(f"Error en /tbodyGastos: {err}")
        return f"<tr><td colspan='4'>Error al cargar datos: {err}</td></tr>"
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/gastos/json")
def gastos_json():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    id_usuario_actual = session['idUsuario']
    gastos_limpios = get_gastos_usuario(id_usuario_actual)
    
    if gastos_limpios is None:
         return make_response(jsonify({"error": "Error al obtener gastos de la BD"}), 500)
    
    return jsonify(gastos_limpios)

@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
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
    except Exception as err:
        print(f"Error en /gasto (agregar): {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_a_eliminar = int(request.form.get("id"))
        id_usuario_actual = session['idUsuario']
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor()
        sql = "DELETE FROM gastos WHERE idGasto = %s AND idUsuario = %s"
        cursor.execute(sql, (id_a_eliminar, id_usuario_actual))
        con.commit()
        notificar_actualizacion_gastos()
        return make_response(jsonify({"status": "success"}), 200)
    except Exception as err:
        print(f"Error en /gasto (eliminar): {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# 4. NUEVA RUTA DE REPORTES (Patrón Factory)
# =========================================================================
@app.route("/exportar/<tipo>")
def exportar_gastos(tipo):
    if 'idUsuario' not in session:
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    try:
        id_usuario_actual = session['idUsuario']
        
        gastos = get_gastos_usuario(id_usuario_actual)
        
        if gastos is None:
            return make_response(jsonify({"error": "No se pudieron obtener los datos para exportar"}), 500)
        
        factory = ReportFactory()
        reporte = factory.crear_reporte(tipo, gastos)
        
        contenido = reporte.generar_reporte()
        
        response = make_response(contenido)
        response.headers['Content-Disposition'] = f'attachment; filename={reporte.get_filename()}'
        response.headers['Content-Type'] = reporte.get_mimetype()
        
        return response

    except ValueError as ve:
        return make_response(jsonify({"error": str(ve)}), 400)
    except Exception as e:
        return make_response(jsonify({"error": f"Error interno del servidor: {e}"}), 500)
# --- FIN DE NUEVA RUTA ---

if __name__ == "__main__":
    app.run(debug=True, port=5000)
