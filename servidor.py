from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
import pusher
from decimal import Decimal
from datetime import date
from datetime import datetime
from report_factory import ReportFactory
from gastos_facade import gastos_facade

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

pusher_client = pusher.Pusher(
    app_id='2050408',
    key='b338714caa5dd2af623d',
    secret='145fd82f4c76138cfdbd',
    cluster='us2',
    ssl=True
)

def notificar_actualizacion_gastos():
    pusher_client.trigger('canal-gastos', 'evento-actualizacion', {'message': 'actualizar'})

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
        id_usuario_actual = session['idUsuario']
        
        username = gastos_facade.get_username_by_id(id_usuario_actual)
        
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
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        
        if gastos_facade.find_user_by_username(usuario):
            return make_response(jsonify({"error": "El nombre de usuario ya está en uso."}), 409)

        if gastos_facade.create_user(usuario, password):
            return make_response(jsonify({"status": "Usuario registrado exitosamente"}), 201)
        else:
            raise Exception("Error al crear usuario")
            
    except Exception as err:
        print(f"Error en /registrarUsuario: {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        
        user_data = gastos_facade.find_user_by_credentials(usuario, password)
        
        if user_data:
            session['idUsuario'] = user_data['idUsuario']
            return make_response(jsonify({"status": "success"}), 200)
        else:
            return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)
    except Exception as err:
        print(f"Error en /iniciarSesion: {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)

@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    session.clear()
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

@app.route("/tbodyGastos")
def tbodyGastos():
    if 'idUsuario' not in session: return "<tr><td colspan='4'>Acceso no autorizado</td></tr>"
    try:
        id_usuario_actual = session['idUsuario']
        
        gastos_ordenados = gastos_facade.get_gastos_for_tbody(id_usuario_actual)
        
        return render_template("tbodyGastos.html", gastos=gastos_ordenados)
    except Exception as err:
        print(f"Error en /tbodyGastos: {err}")
        return f"<tr><td colspan='4'>Error al cargar datos: {err}</td></tr>"

@app.route("/gastos/json")
def gastos_json():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    
    id_usuario_actual = session['idUsuario']
    gastos_limpios = gastos_facade.get_gastos_for_json(id_usuario_actual)
    
    if gastos_limpios is None:
         return make_response(jsonify({"error": "Error al obtener gastos de la BD"}), 500)
    
    return jsonify(gastos_limpios)

@app.route("/gasto", methods=["POST"])
def agregar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    try:
        id_usuario_actual = session['idUsuario']
        
        success = gastos_facade.add_gasto(
            user_id=id_usuario_actual,
            descripcion=request.form.get("descripcion"),
            monto=float(request.form.get("monto")),
            categoria=request.form.get("categoria"),
            fecha=request.form.get("fecha")
        )
        
        if success:
            notificar_actualizacion_gastos()
            return make_response(jsonify({"status": "success"}), 201)
        else:
            raise Exception("Error al agregar gasto")
            
    except Exception as err:
        print(f"Error en /gasto (agregar): {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
    try:
        id_a_eliminar = int(request.form.get("id"))
        id_usuario_actual = session['idUsuario']
        
        success = gastos_facade.delete_gasto(id_a_eliminar, id_usuario_actual)

        if success:
            notificar_actualizacion_gastos()
            return make_response(jsonify({"status": "success"}), 200)
        else:
            raise Exception("Error al eliminar gasto")
            
    except Exception as err:
        print(f"Error en /gasto (eliminar): {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)

@app.route("/exportar/<tipo>")
def exportar_gastos(tipo):
    if 'idUsuario' not in session:
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    try:
        id_usuario_actual = session['idUsuario']
        
        gastos = gastos_facade.get_gastos_for_json(id_usuario_actual)
        
        if gastos is None:
            return make_response(jsonify({"error": "No se pudieron obtener los datos"}), 500)
        
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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
