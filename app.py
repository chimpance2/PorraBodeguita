from flask import Flask, request, jsonify, send_file, render_template
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
# Configura la conexión a la base de datos; si DATABASE_URL no está definida, usa SQLite local
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Variable global para bloquear el envío de predicciones (cuando se bloqueen, ni creación ni modificación)
predicciones_bloqueadas = False
MAX_MODIFICACIONES = 1  # Se permite 1 modificación después del envío inicial

def obtener_fecha_hora():
    now = datetime.now()
    return now.strftime("%d/%m/%Y"), now.strftime("%H:%M")

# Modelos
class Partido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo1 = db.Column(db.String(100), nullable=False)
    equipo2 = db.Column(db.String(100), nullable=False)
    
    def to_dict(self):
        return {"id": self.id, "equipo1": self.equipo1, "equipo2": self.equipo2}

class Prediccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    resultado1 = db.Column(db.String(50), nullable=False)
    resultado2 = db.Column(db.String(50), nullable=False)
    resultado3 = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.String(20), nullable=False)
    hora = db.Column(db.String(10), nullable=False)
    modificaciones = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "resultados": [self.resultado1, self.resultado2, self.resultado3],
            "fecha": self.fecha,
            "hora": self.hora,
            "modificaciones": self.modificaciones
        }

# Rutas e endpoints
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/obtener_partidos', methods=['GET'])
def obtener_partidos():
    partidos = Partido.query.order_by(Partido.id).all()
    return jsonify({"partidos": [p.to_dict() for p in partidos]})

@app.route('/predicciones', methods=['GET'])
def obtener_predicciones():
    preds = Prediccion.query.order_by(Prediccion.fecha.desc()).all()
    return jsonify({"predicciones": [p.to_dict() for p in preds]})

@app.route('/agregar_prediccion', methods=['POST'])
def agregar_prediccion():
    global predicciones_bloqueadas
    if predicciones_bloqueadas:
        return jsonify({"error": "Las predicciones están bloqueadas"}), 403
    data = request.get_json()
    nombre = data.get("nombre")
    resultados = data.get("resultados", [])
    if len(resultados) < 3:
        return jsonify({"error": "Se requieren 3 resultados"}), 400
    fecha, hora = obtener_fecha_hora()
    # Validar duplicados de 3 resultados entre diferentes usuarios
    existing = Prediccion.query.filter(Prediccion.nombre != nombre,
                                       Prediccion.resultado1==resultados[0],
                                       Prediccion.resultado2==resultados[1],
                                       Prediccion.resultado3==resultados[2]).first()
    if existing:
        return jsonify({"error": "Ya existe una predicción idéntica de otro usuario"}), 400
    # Verificar si existe alguna predicción con 2 de 3 resultados iguales (aviso)
    warning = ""
    others = Prediccion.query.filter(Prediccion.nombre != nombre).all()
    for o in others:
        coincidencias = sum(1 for a,b in zip([o.resultado1, o.resultado2, o.resultado3], resultados) if a==b)
        if coincidencias == 2:
            warning = "Atención: Tu predicción coincide en 2 de 3 resultados con otra predicción."
    new_pred = Prediccion(nombre=nombre,
                          resultado1=resultados[0],
                          resultado2=resultados[1],
                          resultado3=resultados[2],
                          fecha=fecha,
                          hora=hora,
                          modificaciones=0)
    db.session.add(new_pred)
    db.session.commit()
    response = {"mensaje": "Predicción agregada con éxito"}
    if warning:
        response["warning"] = warning
    return jsonify(response)

@app.route('/modificar_prediccion', methods=['PUT'])
def modificar_prediccion():
    global predicciones_bloqueadas
    if predicciones_bloqueadas:
        return jsonify({"error": "Las predicciones están bloqueadas"}), 403
    data = request.get_json()
    nombre = data.get("nombre")
    nuevos_resultados = data.get("resultados", [])
    if len(nuevos_resultados) < 3:
        return jsonify({"error": "Se requieren 3 resultados"}), 400
    pred = Prediccion.query.filter_by(nombre=nombre).first()
    if not pred:
        return jsonify({"error": "Predicción no encontrada"}), 404
    if pred.modificaciones >= MAX_MODIFICACIONES:
        return jsonify({"error": "Ya has alcanzado el máximo de modificaciones permitidas"}), 403
    existing = Prediccion.query.filter(Prediccion.nombre != nombre,
                                       Prediccion.resultado1==nuevos_resultados[0],
                                       Prediccion.resultado2==nuevos_resultados[1],
                                       Prediccion.resultado3==nuevos_resultados[2]).first()
    if existing:
        return jsonify({"error": "Ya existe una predicción idéntica de otro usuario"}), 400
    warning = ""
    others = Prediccion.query.filter(Prediccion.nombre != nombre).all()
    for o in others:
        coincidencias = sum(1 for a,b in zip([o.resultado1, o.resultado2, o.resultado3], nuevos_resultados) if a==b)
        if coincidencias == 2:
            warning = "Atención: Tu nueva predicción coincide en 2 de 3 resultados con otra predicción."
    pred.resultado1 = nuevos_resultados[0]
    pred.resultado2 = nuevos_resultados[1]
    pred.resultado3 = nuevos_resultados[2]
    pred.modificaciones += 1
    fecha, hora = obtener_fecha_hora()
    pred.fecha = fecha
    pred.hora = hora
    db.session.commit()
    response = {"mensaje": "Predicción modificada con éxito"}
    if warning:
        response["warning"] = warning
    return jsonify(response)

@app.route('/actualizar_partidos', methods=['POST'])
def actualizar_partidos():
    global predicciones_bloqueadas
    data = request.get_json()
    clave = data.get("clave")
    if clave != "admin123":
        return jsonify({"error": "Clave incorrecta"}), 403
    partidos_data = data.get("partidos", [])
    if len(partidos_data) != 3:
        return jsonify({"error": "Se deben enviar 3 partidos"}), 400
    for partido in partidos_data:
        p = Partido.query.filter_by(id=partido.get("id")).first()
        if p:
            p.equipo1 = partido.get("equipo1")
            p.equipo2 = partido.get("equipo2")
        else:
            new_p = Partido(id=partido.get("id"),
                            equipo1=partido.get("equipo1"),
                            equipo2=partido.get("equipo2"))
            db.session.add(new_p)
    db.session.commit()
    # Reiniciamos las predicciones para la nueva semana
    Prediccion.query.delete()
    db.session.commit()
    predicciones_bloqueadas = False
    return jsonify({"mensaje": "Partidos actualizados y predicciones reiniciadas."})

@app.route('/bloquear_predicciones', methods=['POST'])
def bloquear_predicciones():
    global predicciones_bloqueadas
    data = request.get_json()
    clave = data.get("clave")
    if clave != "admin123":
        return jsonify({"error": "Clave incorrecta"}), 403
    bloquear = data.get("bloquear")
    if bloquear is None:
        return jsonify({"error": "Se debe enviar el parámetro 'bloquear' (true o false)"}), 400
    predicciones_bloqueadas = bool(bloquear)
    estado = "bloqueadas" if predicciones_bloqueadas else "desbloqueadas"
    return jsonify({"mensaje": f"Las predicciones han sido {estado}."})

# ********* Endpoint temporal para ejecutar migraciones *********
# ¡ATENCIÓN! Este endpoint se usa únicamente para ejecutar las migraciones
# y debe eliminarse o desactivarse una vez que se hayan aplicado correctamente.
@app.route('/run_migration', methods=['POST'])
def run_migration():
    clave = request.args.get("clave")
    if clave != "admin123":
        return jsonify({"error": "Acceso denegado"}), 403
    from flask_migrate import upgrade
    try:
        upgrade()
        return jsonify({"mensaje": "Migraciones ejecutadas correctamente."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/descargar_predicciones', methods=['GET'])
def descargar_predicciones():
    preds = Prediccion.query.order_by(Prediccion.fecha.desc()).all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Predicciones Semanales", ln=True, align='C')
    for pred in preds:
        pdf.cell(200, 10, txt=f"Usuario: {pred.nombre}; Resultados: [{pred.resultado1}, {pred.resultado2}, {pred.resultado3}]; Fecha: {pred.fecha}; Hora: {pred.hora}", ln=True)
    filename = "predicciones.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
