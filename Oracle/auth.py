"""
Utilidades de autenticación para el panel de admin.
Las contraseñas NUNCA se guardan en texto plano — solo su hash.
"""
from functools import wraps
from flask import session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash


def generar_hash(password_plano: str) -> str:
    """Convierte una contraseña en texto plano a su hash seguro para guardar en ADMINS.PASSWORD_HASH."""
    return generate_password_hash(password_plano)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara la contraseña que escribió el admin contra el hash guardado en la base de datos."""
    return check_password_hash(password_hash, password_plano)


def login_required(f):
    """
    Decorador para proteger rutas del panel: si no hay sesión de admin activa,
    redirige al login. Ponerlo en TODAS las rutas del panel excepto /login.
    """
    @wraps(f)
    def decorada(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorada
