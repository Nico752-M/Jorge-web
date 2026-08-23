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

    if not nombre or not telefono:
        return jsonify({"ok": False, "error": "Faltan nombre o teléfono."}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO SOLICITUDES_ALQUILER
               (NOMBRE, TELEFONO, FECHA_DESEADA, RANGO_HORA_APROX, TIPO_EVENTO, ESTADO)
           VALUES (:nombre, :telefono, TO_DATE(:fecha, 'YYYY-MM-DD'), :rango, :tipo, 'PENDIENTE')""",
        nombre=nombre,
        telefono=telefono,
        fecha=fecha_deseada,
        rango=rango_hora,
        tipo=tipo_evento,
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
        """SELECT ID, NOMBRE, TELEFONO, FECHA_DESEADA, RANGO_HORA_APROX, TIPO_EVENTO, ESTADO
           FROM SOLICITUDES_ALQUILER
           WHERE ESTADO IN ('PENDIENTE', 'CONTACTADO')
           ORDER BY FECHA_SOLICITUD DESC"""
    )
    solicitudes = cur.fetchall()

    cur.execute(
        """SELECT ID, TIPO, TITULO, FECHA_INICIO, FECHA_FIN, AFORO_DISPONIBLE, AFORO_TOTAL
           FROM EVENTOS
           WHERE ESTADO = 'ACTIVO'
           ORDER BY FECHA_INICIO"""
    )
    eventos = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("dashboard.html", solicitudes=solicitudes, eventos=eventos)


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

        # --- Crear el evento tipo ALQUILER ---
        nuevo_id_var = cur.var(oracledb.NUMBER)
        cur.execute(
            """INSERT INTO EVENTOS (TIPO, TITULO, FECHA_INICIO, FECHA_FIN, PRECIO_FINAL, CREADO_POR)
               VALUES ('ALQUILER', :titulo,
                       TO_TIMESTAMP(:inicio, 'YYYY-MM-DD HH24:MI'),
                       TO_TIMESTAMP(:fin, 'YYYY-MM-DD HH24:MI'),
                       :precio, :admin_id)
               RETURNING ID INTO :nuevo_id""",
            titulo=titulo,
            inicio=fecha_inicio_str,
            fin=fecha_fin_str,
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
        """SELECT ID, NOMBRE, TELEFONO, FECHA_DESEADA, RANGO_HORA_APROX, TIPO_EVENTO
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
