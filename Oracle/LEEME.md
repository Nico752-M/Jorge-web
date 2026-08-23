# Café Real — Despliegue en Vercel

## Cómo debe quedar la raíz de tu proyecto (Jorge-web)

```
Jorge-web/
├── public/                   ← NUEVO: mover aquí tu index.html y tu carpeta images/
│   ├── index.html            ← lo mueves tú (el que ya tenías)
│   ├── images/                ← lo mueves tú
│   └── admin.css             ← estilos del panel (ya viene aquí)
├── Oracle/
│   ├── __init__.py            ← nuevo, vacío, para que Vercel encuentre la app
│   ├── app.py
│   ├── auth.py
│   ├── rutas/
│   │   └── db.py
│   ├── templates/
│   ├── scripts/crear_admin.py
│   ├── wallet/                ← aquí va el wallet descomprimido
│   └── tablas-cafe-real.sql
├── requirements.txt           ← NUEVO en la raíz (Vercel lo necesita aquí)
├── pyproject.toml             ← NUEVO, le dice a Vercel dónde está la app de Flask
└── vercel.json                ← NUEVO, configura el tiempo máximo de la función
```

## Dos cosas que tienes que mover tú a mano

1. **Tu `index.html` y tu carpeta `images/`** tienen que quedar dentro de una
   carpeta llamada `public/` en la raíz (Vercel solo sirve como sitio estático
   lo que está ahí adentro). Dentro de ese zip ya te dejé `public/admin.css`
   creada — solo arrastra tu `index.html` e `images/` ahí mismo.
2. Borra (o ignora) tu `requeriments.txt` viejo dentro de `Oracle/rutas/` —
   ya no se usa, quedó un archivo `LEER_ESTO.txt` explicándolo. El que cuenta
   ahora es el `requirements.txt` de la raíz.

## Pasos para desplegar

1. **Sube todo esto a un repositorio de GitHub** (Vercel se conecta a GitHub
   para desplegar automáticamente con cada cambio que subas).

2. **En Vercel:** "Add New Project" → conecta ese repositorio → dale "Deploy".
   No necesitas tocar el Build Command, Vercel detecta Flask solo gracias al
   `pyproject.toml`.

3. **Configura las variables de entorno en Vercel** (esto reemplaza tu `.env`,
   que solo sirve para tu máquina local — en Vercel se configuran desde el
   dashboard del proyecto → Settings → Environment Variables):
   - `SECRET_KEY`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_DSN`
   - `WALLET_PASSWORD` (solo si tu wallet tiene contraseña)
   - No necesitas poner `WALLET_DIR` — ahora se calcula solo.

4. **El wallet de Oracle debe quedar subido dentro de `Oracle/wallet/`** en tu
   repositorio de GitHub (borra el archivo `PON_AQUI_EL_WALLET.txt`, ya no se
   necesita). Sí, técnicamente el wallet queda en el repo — mientras el
   repositorio sea privado, no hay problema.

5. Cada vez que hagas `git push`, Vercel vuelve a desplegar solo — ahí vas a
   ver los cambios reflejados casi en tiempo real, como querías.

## Cómo queda accediendo

- Sitio público: `https://tudominio.vercel.app/` (tu `index.html`)
- Panel admin: `https://tudominio.vercel.app/panel-cr8x/login`

   Antes de que esto sea público de verdad, cambia `ADMIN_PREFIX` en
   `Oracle/app.py` (línea con `ADMIN_PREFIX = "/panel-cr8x"`) por algo que
   solo ustedes conozcan.

## Para seguir probando en tu máquina (sin Vercel)

```
cd Oracle
python -m venv venv
venv\Scripts\activate            (Mac/Linux: source venv/bin/activate)
pip install -r ../requirements.txt
python app.py
```
Entra por `http://localhost:5000/panel-cr8x/login`. En local, el CSS lo vas a
tener que servir tú mismo o copiar `public/admin.css` temporalmente dentro de
una carpeta `static/` en `Oracle/` si quieres verlo bonito sin Vercel — o
simplemente prueba ya directo desde Vercel, que es más fiel a como va a quedar.
