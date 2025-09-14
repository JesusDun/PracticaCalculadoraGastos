# Archivo: servidor.py
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import pusher
import time

# --- Configuración de la Aplicación ---
app = Flask(__name__)
CORS(app)

# --- Configuración de Pusher ---
pusher_client = pusher.Pusher(
  app_id='2050408',
  key='b338714caa5dd2af623d',
  secret='145fd82f4c76138cfdbd',
  cluster='us2',
  ssl=True
)

# --- "Base de Datos" en Memoria (sin base de datos real) ---
# Guardaremos los usuarios y los gastos aquí mientras el servidor esté activo.
usuarios_db = {
    "admin": "12345"
}
gastos_db = []
gasto_id_counter = 1 # Para generar IDs únicos para cada gasto

# --- Rutas de la API ---

# 1. RUTA DE INICIO DE SESIÓN
@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username in usuarios_db and usuarios_db[username] == password:
        # Login exitoso
        return make_response(jsonify({"message": "Login exitoso"}), 200)
    else:
        # Login fallido
        return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)

# 2. RUTA PARA OBTENER TODOS LOS GASTOS
@app.route("/gastos", methods=["GET"])
def obtener_gastos():
    # Devolvemos la lista de gastos ordenada del más nuevo al más viejo
    return jsonify(sorted(gastos_db, key=lambda x: x['id'], reverse=True))

# 3. RUTA PARA AGREGAR UN GASTO
@app.route("/gastos", methods=["POST"])
def agregar_gasto():
    global gasto_id_counter
    nuevo_gasto = request.get_json()

    # Creamos el objeto de gasto completo en el servidor
    gasto_servidor = {
        "id": gasto_id_counter,
        "description": nuevo_gasto.get("description"),
        "amount": float(nuevo_gasto.get("amount")),
        "category": nuevo_gasto.get("category"),
        "date": nuevo_gasto.get("date")
    }
    
    gastos_db.append(gasto_servidor)
    gasto_id_counter += 1
    
    # Notificamos a todos los clientes a través de Pusher
    pusher_client.trigger('canal-gastos', 'evento-gastos', {'message': 'actualizar'})
    
    return make_response(jsonify(gasto_servidor), 201)

# 4. RUTA PARA ELIMINAR UN GASTO
@app.route("/gastos/<int:id>", methods=["DELETE"])
def eliminar_gasto(id):
    global gastos_db
    # Filtramos la lista para quitar el gasto con el ID correspondiente
    gasto_encontrado = any(gasto['id'] == id for gasto in gastos_db)
    
    if not gasto_encontrado:
        return make_response(jsonify({"error": "Gasto no encontrado"}), 404)
        
    gastos_db = [gasto for gasto in gastos_db if gasto['id'] != id]
    
    # Notificamos a todos los clientes a través de Pusher
    pusher_client.trigger('canal-gastos', 'evento-gastos', {'message': 'actualizar'})
    
    return make_response(jsonify({"message": "Gasto eliminado"}), 200)

# --- Ejecutar el Servidor ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
