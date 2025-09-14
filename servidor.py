# Archivo: servidor.py
from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import pusher

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

# --- "Base de Datos" en Memoria ---
usuarios_db = {"admin": "12345"}
gastos_db = []
gasto_id_counter = 1

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
# API PARA LA LÓGICA DE LA APLICACIÓN
# =========================================================================

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    usuario = request.form.get("txtUsuario")
    password = request.form.get("txtContrasena")

    if usuario in usuarios_db and usuarios_db[usuario] == password:
        return make_response(jsonify({"status": "success"}), 200)
    else:
        return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)

# --- RUTA PARA DEVOLVER LOS GASTOS A LA TABLA (HTML) ---
@app.route("/tbodyGastos")
def tbodyGastos():
    # Ordenamos los gastos del más nuevo al más viejo
    gastos_ordenados = sorted(gastos_db, key=lambda x: x['id'], reverse=True)
    return render_template("tbodyGastos.html", gastos=gastos_ordenados)

# --- RUTA PARA DEVOLVER LOS GASTOS A LOS GRÁFICOS (JSON) ---
@app.route("/gastos/json")
def gastos_json():
    return jsonify(gastos_db)

# --- RUTA PARA AGREGAR UN GASTO ---
@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    global gasto_id_counter
    nuevo_gasto = {
        "id": gasto_id_counter,
        "description": request.form.get("description"),
        "amount": float(request.form.get("amount")),
        "category": request.form.get("category"),
        "date": request.form.get("date")
    }
    gastos_db.append(nuevo_gasto)
    gasto_id_counter += 1
    
    notificar_actualizacion_gastos()
    return make_response(jsonify({"status": "success"}), 201)

# --- RUTA PARA ELIMINAR UN GASTO ---
@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    global gastos_db
    id_a_eliminar = int(request.form.get("id"))
    gastos_db = [gasto for gasto in gastos_db if gasto['id'] != id_a_eliminar]
    
    notificar_actualizacion_gastos()
    return make_response(jsonify({"status": "success"}), 200)

# --- Ejecutar el Servidor ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
