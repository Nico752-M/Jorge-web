"""
Conexión a la base de datos Oracle Autonomous Database.
Usa python-oracledb en modo 'thin' (no necesita instalar Oracle Instant Client),
conectándose con la carpeta del wallet que descargas desde la consola de OCI.
"""
import os
import oracledb

# Carpeta de este archivo (rutas/) -> subimos un nivel para llegar a Oracle/wallet
# Así funciona igual en tu máquina y en Vercel, sin importar desde dónde se ejecute.
_CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
_WALLET_POR_DEFECTO = os.path.join(_CARPETA_ACTUAL, "..", "wallet")


def get_connection():
    """
    Abre y devuelve una nueva conexión a la base de datos.
    Se abre una conexión nueva por cada request y se cierra al final
    (ver ejemplos en app.py) — así no se acumulan conexiones colgadas.
    """
    wallet_dir = os.environ.get("WALLET_DIR", _WALLET_POR_DEFECTO)
    return oracledb.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=os.environ["DB_DSN"],               # ej: "cafejorge_high" (viene del tnsnames.ora del wallet)
        config_dir=wallet_dir,
        wallet_location=wallet_dir,
        wallet_password=os.environ.get("WALLET_PASSWORD"),  # solo si le pusiste contraseña al wallet
    )
