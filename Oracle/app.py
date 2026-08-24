"""
Panel de administración de Café Real.
Ruta oculta: cámbiala en ADMIN_PREFIX por algo que solo ustedes conozcan
(no dejes '/panel-cr8x', invéntate otra combinación).
"""
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

import oracledb
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash

from rutas.db import get_connection
from auth import login_required, verificar_password

load_dotenv()

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "public"),
    static_url_path="",
)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-por-algo-largo-y-aleatorio")

# ---- Ruta oculta del panel: cámbiala antes de publicar el sitio ----
ADMIN_PREFIX = "/panel-cr8x"


# =========================================================
# LOGIN / LOGOUT
# =========================================================
@app.route(f"{ADMIN_PREFIX}/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT ID, PASSWORD_HASH FROM ADMINS WHERE USUARIO = :u AND ACTIVO = 1",
            u=usuario,
        )
        fila = cur.fetchone()
        cur.close()
        conn.close()

        if fila and verificar_password(password, fila[1]):
            session["admin_id"] = fila[0]
            session["admin_usuario"] = usuario
            return redirect(url_for("dashboard"))

        flash("Usuario o contraseña incorrectos.")

    return render_template("login.html")


@app.route(f"{ADMIN_PREFIX}/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================================================
# SOLICITUD PÚBLICA DE ALQUILER (sin login — la llama index.html)
# =========================================================

@app.route("/api/solicitudes-alquiler", methods=["POST"])
def crear_solicitud_alquiler():
    data = request.get_json(silent=True) or {}

    nombre = (data.get("nombre") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    fecha_deseada = data.get("fecha_deseada") or None
    rango_hora = (data.get("rango_hora_aprox") or "").strip()
    tipo_evento = (data.get("tipo_evento") or "").strip()
    num_personas = data.get("num_personas") or None

    if not nombre or not telefono:
        return jsonify({"ok": False, "error": "Faltan nombre o teléfono."}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO SOLICITUDES_ALQUILER
               (NOMBRE, TELEFONO, FECHA_DESEADA, RANGO_HORA_APROX, TIPO_EVENTO, NUM_PERSONAS, ESTADO)
           VALUES (:nombre, :telefono, TO_DATE(:fecha, 'YYYY-MM-DD'), :rango, :tipo, :personas, 'PENDIENTE')""",
        nombre=nombre,
        telefono=telefono,
        fecha=fecha_deseada,
        rango=rango_hora,
        tipo=tipo_evento,
        personas=num_personas,
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

# =========================================================
# DASHBOARD — bandeja de solicitudes + lista de eventos
# =========================================================
@app.route(f"{ADMIN_PREFIX}/")
@app.route(f"{ADMIN_PREFIX}/dashboard")
@login_required
def dashboard():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """SELECT ID, NOMBRE, TELEFONO, FECHA_DESEADA, RANGO_HORA_APROX, TIPO_EVENTO, NUM_PERSONAS, ESTADO
           FROM SOLICITUDES_ALQUILER
           WHERE ESTADO IN ('PENDIENTE', 'CONTACTADO')
           ORDER BY FECHA_SOLICITUD DESC"""
    )
    solicitudes = cur.fetchall()

    cur.execute(
        """SELECT ID, TIPO, TITULO, DESCRIPCION, FECHA_INICIO, FECHA_FIN, AFORO_DISPONIBLE, AFORO_TOTAL, VISIBLE_PUBLICO
           FROM EVENTOS
           WHERE ESTADO = 'ACTIVO'
           ORDER BY FECHA_INICIO"""
    )
    eventos = cur.fetchall()

    cur.execute(
        """SELECT r.ID, r.NOMBRE, r.APELLIDO, r.TELEFONO, r.NUM_PERSONAS, r.FECHA_RESERVA,
                  e.ID, e.TITULO, e.AFORO_TOTAL, e.AFORO_DISPONIBLE
           FROM RESERVAS_CUPOS r
           JOIN EVENTOS e ON e.ID = r.EVENTO_ID
           WHERE r.ESTADO = 'EXCEDENTE'
           ORDER BY r.FECHA_RESERVA"""
    )
    excedentes = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("dashboard.html", solicitudes=solicitudes, eventos=eventos, excedentes=excedentes)
# =========================================================
# ACCIONES SOBRE SOLICITUDES DE ALQUILER
# =========================================================
@app.route(f"{ADMIN_PREFIX}/solicitud/<int:solicitud_id>/marcar_contactado")
@login_required
def marcar_contactado(solicitud_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE SOLICITUDES_ALQUILER SET ESTADO = 'CONTACTADO' WHERE ID = :id",
        id=solicitud_id,
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route(f"{ADMIN_PREFIX}/solicitud/<int:solicitud_id>/rechazar")
@login_required
def rechazar_solicitud(solicitud_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE SOLICITUDES_ALQUILER SET ESTADO = 'RECHAZADO' WHERE ID = :id",
        id=solicitud_id,
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route(f"{ADMIN_PREFIX}/solicitud/<int:solicitud_id>/confirmar", methods=["GET", "POST"])
@login_required
def confirmar_solicitud(solicitud_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        fecha = request.form["fecha"]
        hora_inicio = request.form["hora_inicio"]
        hora_fin = request.form["hora_fin"]
        precio = request.form["precio_final"]
        titulo = request.form["titulo"].strip()
        aforo_total = request.form["aforo_total"]
        visible_publico = 1 if request.form.get("visible_publico") == "on" else 0

        fecha_inicio_str = f"{fecha} {hora_inicio}"
        fecha_fin_str = f"{fecha} {hora_fin}"

        # --- Validar que no se cruce con otro alquiler ya confirmado ---
        cur.execute(
            """SELECT COUNT(*) FROM EVENTOS
               WHERE TIPO = 'ALQUILER' AND ESTADO = 'ACTIVO'
               AND FECHA_INICIO < TO_TIMESTAMP(:fin, 'YYYY-MM-DD HH24:MI')
               AND FECHA_FIN     > TO_TIMESTAMP(:inicio, 'YYYY-MM-DD HH24:MI')""",
            fin=fecha_fin_str,
            inicio=fecha_inicio_str,
        )
        cruces = cur.fetchone()[0]

        if cruces > 0:
            flash("Ese horario se cruza con otro alquiler ya confirmado. Elige otra hora.")
            cur.close()
            conn.close()
            return redirect(url_for("confirmar_solicitud", solicitud_id=solicitud_id))

        # --- Crear el evento tipo ALQUILER (con aforo, como cualquier evento con cupos) ---
        nuevo_id_var = cur.var(oracledb.NUMBER)
        cur.execute(
            """INSERT INTO EVENTOS (TIPO, TITULO, FECHA_INICIO, FECHA_FIN, AFORO_TOTAL, AFORO_DISPONIBLE, VISIBLE_PUBLICO, PRECIO_FINAL, CREADO_POR)
               VALUES ('ALQUILER', :titulo,
                       TO_TIMESTAMP(:inicio, 'YYYY-MM-DD HH24:MI'),
                       TO_TIMESTAMP(:fin, 'YYYY-MM-DD HH24:MI'),
                       :aforo, :aforo, :visible, :precio, :admin_id)
               RETURNING ID INTO :nuevo_id""",
            titulo=titulo,
            inicio=fecha_inicio_str,
            fin=fecha_fin_str,
            aforo=aforo_total,
            visible=visible_publico,
            precio=precio,
            admin_id=session["admin_id"],
            nuevo_id=nuevo_id_var,
        )
        nuevo_evento_id = int(nuevo_id_var.getvalue()[0])

        # --- Enlazar la solicitud con el evento ya creado ---
        cur.execute(
            """UPDATE SOLICITUDES_ALQUILER
               SET ESTADO = 'CONFIRMADO', EVENTO_ID = :evento_id
               WHERE ID = :id""",
            evento_id=nuevo_evento_id,
            id=solicitud_id,
        )

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))

    # GET: mostrar el formulario con los datos de la solicitud
    cur.execute(
        """SELECT ID, NOMBRE, TELEFONO, FECHA_DESEADA, RANGO_HORA_APROX, TIPO_EVENTO, NUM_PERSONAS
           FROM SOLICITUDES_ALQUILER WHERE ID = :id""",
        id=solicitud_id,
    )
    solicitud = cur.fetchone()
    cur.close()
    conn.close()

    if not solicitud:
        flash("Esa solicitud ya no existe.")
        return redirect(url_for("dashboard"))

    return render_template("confirmar_solicitud.html", s=solicitud)

# =========================================================
# CREAR EVENTO CON CUPOS (organizado por el local)
# =========================================================
@app.route(f"{ADMIN_PREFIX}/evento/nuevo", methods=["GET", "POST"])
@login_required
def evento_nuevo():
    if request.method == "POST":
        titulo = request.form["titulo"].strip()
        descripcion = request.form.get("descripcion", "").strip()
        fecha_inicio = request.form["fecha_inicio"]     # "YYYY-MM-DD"
        hora_inicio = request.form["hora_inicio"]        # "HH:MM"
        fecha_fin = request.form.get("fecha_fin") or fecha_inicio
        hora_fin = request.form.get("hora_fin") or hora_inicio
        aforo_total = request.form["aforo_total"]
        visible_publico = 1 if request.form.get("visible_publico") == "on" else 0

        inicio_str = f"{fecha_inicio} {hora_inicio}"
        fin_str = f"{fecha_fin} {hora_fin}"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO EVENTOS (TIPO, TITULO, DESCRIPCION, FECHA_INICIO, FECHA_FIN,
                                     AFORO_TOTAL, AFORO_DISPONIBLE, VISIBLE_PUBLICO, CREADO_POR)
               VALUES ('CUPOS', :titulo, :descripcion,
                       TO_TIMESTAMP(:inicio, 'YYYY-MM-DD HH24:MI'),
                       TO_TIMESTAMP(:fin, 'YYYY-MM-DD HH24:MI'),
                       :aforo, :aforo, :visible, :admin_id)""",
            titulo=titulo,
            descripcion=descripcion or None,
            inicio=inicio_str,
            fin=fin_str,
            aforo=aforo_total,
            visible=visible_publico,
            admin_id=session["admin_id"],
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))

    return render_template("evento_nuevo.html")

@app.route(f"{ADMIN_PREFIX}/evento/<int:evento_id>/toggle_visible")
@login_required
def toggle_visible_evento(evento_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE EVENTOS SET VISIBLE_PUBLICO = 1 - VISIBLE_PUBLICO WHERE ID = :id",
        id=evento_id,
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route(f"{ADMIN_PREFIX}/reserva-cupo/<int:reserva_id>/ampliar")
@login_required
def ampliar_reserva_cupo(reserva_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT EVENTO_ID, NUM_PERSONAS FROM RESERVAS_CUPOS WHERE ID = :id AND ESTADO = 'EXCEDENTE'",
        id=reserva_id,
    )
    fila = cur.fetchone()
    if fila:
        evento_id, num_personas = fila
        # Se amplía el aforo total exactamente lo necesario para esta reserva;
        # como esos cupos nuevos ya quedan ocupados por ella, AFORO_DISPONIBLE no cambia.
        cur.execute(
            "UPDATE EVENTOS SET AFORO_TOTAL = AFORO_TOTAL + :n WHERE ID = :id",
            n=num_personas, id=evento_id,
        )
        cur.execute(
            "UPDATE RESERVAS_CUPOS SET ESTADO = 'CONFIRMADA' WHERE ID = :id",
            id=reserva_id,
        )
        conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route(f"{ADMIN_PREFIX}/reserva-cupo/<int:reserva_id>/rechazar")
@login_required
def rechazar_reserva_cupo(reserva_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE RESERVAS_CUPOS SET ESTADO = 'RECHAZADA' WHERE ID = :id AND ESTADO = 'EXCEDENTE'",
        id=reserva_id,
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

# =========================================================
# EVENTOS PÚBLICOS Y RESERVA DE CUPOS (sin login — los llama index.html)
# =========================================================
@app.route("/api/eventos-publicos")
def eventos_publicos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT ID, TITULO, DESCRIPCION, FECHA_INICIO, FECHA_FIN, AFORO_TOTAL, AFORO_DISPONIBLE
           FROM EVENTOS
           WHERE VISIBLE_PUBLICO = 1 AND ESTADO = 'ACTIVO' AND FECHA_INICIO >= SYSTIMESTAMP
           ORDER BY FECHA_INICIO"""
    )
    filas = cur.fetchall()
    cur.close()
    conn.close()

    eventos = [
        {
            "id": f[0],
            "titulo": f[1],
            "descripcion": f[2],
            "fecha_inicio": f[3].isoformat() if f[3] else None,
            "fecha_fin": f[4].isoformat() if f[4] else None,
            "aforo_total": f[5],
            "aforo_disponible": f[6],
        }
        for f in filas
    ]
    return jsonify(eventos)


@app.route("/api/reservas-cupo", methods=["POST"])
def crear_reserva_cupo():
    data = request.get_json(silent=True) or {}

    evento_id = data.get("evento_id")
    nombre = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    num_personas = data.get("num_personas")

    if not evento_id or not nombre or not telefono or not num_personas:
        return jsonify({"ok": False, "error": "Faltan datos."}), 400

    try:
        num_personas = int(num_personas)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Número de personas inválido."}), 400

    if num_personas < 1:
        return jsonify({"ok": False, "error": "Número de personas inválido."}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT ID FROM EVENTOS WHERE ID = :id AND VISIBLE_PUBLICO = 1 AND ESTADO = 'ACTIVO'",
        id=evento_id,
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Ese evento ya no está disponible."}), 404

    # Intento atómico: solo resta si de verdad alcanzan los cupos.
    cur.execute(
        """UPDATE EVENTOS
           SET AFORO_DISPONIBLE = AFORO_DISPONIBLE - :n
           WHERE ID = :id AND AFORO_DISPONIBLE >= :n""",
        n=num_personas,
        id=evento_id,
    )
    alcanzo = cur.rowcount == 1
    estado_reserva = "CONFIRMADA" if alcanzo else "EXCEDENTE"

    cur.execute(
        """INSERT INTO RESERVAS_CUPOS (EVENTO_ID, NOMBRE, APELLIDO, TELEFONO, NUM_PERSONAS, ESTADO)
           VALUES (:evento_id, :nombre, :apellido, :telefono, :num_personas, :estado)""",
        evento_id=evento_id,
        nombre=nombre,
        apellido=apellido or None,
        telefono=telefono,
        num_personas=num_personas,
        estado=estado_reserva,
    )

    conn.commit()
    cur.close()
    conn.close()

    if alcanzo:
        return jsonify({"ok": True, "confirmado": True})

    return jsonify({
        "ok": True,
        "confirmado": False,
        "mensaje": "Por ahora no quedan cupos suficientes. Guardamos tu solicitud — estamos viendo si se puede ampliar el aforo y te contactaremos."
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
