from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime
from app_mediator import app_mediator

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

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
    response, code = app_mediator.registrar_usuario(request.form)
    return make_response(jsonify(response), code)

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    response, code = app_mediator.iniciar_sesion(request.form)
    if code == 200:
        session['idUsuario'] = response["user_id"]
        return make_response(jsonify(response), code)

@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    session.clear()
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

@app.route("/tbodyGastos")
def tbodyGastos():
    if 'idUsuario' not in session:
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
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    response, code = app_mediator.agregar_gasto(session['idUsuario'], request.form)
    return make_response(jsonify(response), code)

@app.route("/gasto/eliminar", methods=["POST"])
def eliminar_gasto():
    if 'idUsuario' not in session:
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    response, code = app_mediator.eliminar_gasto(session['idUsuario'], request.form)
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
        
    except ValueError as ve:
        return make_response(jsonify({"error": str(ve)}), 400)
    except Exception as e:
        print(f"Error en /exportar: {e}")
        return make_response(jsonify({"error": f"Error interno del servidor: {e}"}), 500)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
