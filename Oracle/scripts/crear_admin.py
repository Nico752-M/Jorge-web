"""
Crea un admin nuevo en la tabla ADMINS.

Úsalo la primera vez para tener con quién entrar al panel, y cada vez
que quieran dar acceso a un nuevo empleado.

Cómo correrlo (desde la carpeta backend/):
    python scripts/crear_admin.py
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from rutas.db import get_connection
from auth import generar_hash

def main():
    nombre = input("Nombre completo: ").strip()
    usuario = input("Usuario (con el que va a iniciar sesión): ").strip()
    password = input("Contraseña: ").strip()

    if not nombre or not usuario or not password:
        print("Todos los campos son obligatorios.")
        return

    password_hash = generar_hash(password)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ADMINS (NOMBRE, USUARIO, PASSWORD_HASH) VALUES (:n, :u, :p)",
        n=nombre, u=usuario, p=password_hash,
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Listo. El usuario '{usuario}' ya puede iniciar sesión en el panel.")

if __name__ == "__main__":
    main()
