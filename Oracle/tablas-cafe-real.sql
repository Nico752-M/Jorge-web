-- =========================================================
-- CAFÉ REAL — Diseño de tablas (Oracle Autonomous Database)
-- Ejecutar en Database Actions > SQL, conectado como ADMIN
-- (o mejor, crear un usuario/esquema propio para la app, ver nota al final)
-- =========================================================

-- ---------------------------------------------------------
-- 1. ADMINS: los únicos que pueden iniciar sesión
-- ---------------------------------------------------------
CREATE TABLE ADMINS (
  ID              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NOMBRE          VARCHAR2(100) NOT NULL,
  USUARIO         VARCHAR2(50)  NOT NULL UNIQUE,
  PASSWORD_HASH   VARCHAR2(255) NOT NULL,   -- nunca guardar la contraseña en texto plano
  ACTIVO          NUMBER(1) DEFAULT 1 CHECK (ACTIVO IN (0,1)),
  FECHA_CREACION  TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ---------------------------------------------------------
-- 2. EVENTOS: cubre tanto "evento con cupos" como "alquiler"
-- ---------------------------------------------------------
CREATE TABLE EVENTOS (
  ID               NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  TIPO             VARCHAR2(20) NOT NULL CHECK (TIPO IN ('CUPOS','ALQUILER')),
  TITULO           VARCHAR2(150) NOT NULL,
  DESCRIPCION      VARCHAR2(1000),
  FECHA_INICIO     TIMESTAMP NOT NULL,   -- fecha+hora del evento (cupos) o inicio del alquiler
  FECHA_FIN        TIMESTAMP,            -- solo aplica a ALQUILER
  AFORO_TOTAL      NUMBER,               -- solo aplica a CUPOS
  AFORO_DISPONIBLE NUMBER,               -- solo aplica a CUPOS, se va descontando
  PRECIO_FINAL     NUMBER(10,2),         -- solo aplica a ALQUILER, lo llena el admin al confirmar
  ESTADO           VARCHAR2(20) DEFAULT 'ACTIVO' CHECK (ESTADO IN ('ACTIVO','CANCELADO','FINALIZADO')),
  CREADO_POR       NUMBER REFERENCES ADMINS(ID),
  FECHA_CREACION   TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ---------------------------------------------------------
-- 3. RESERVAS_CUPOS: reservas de clientes a eventos con cupos
-- ---------------------------------------------------------
CREATE TABLE RESERVAS_CUPOS (
  ID             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  EVENTO_ID      NUMBER NOT NULL REFERENCES EVENTOS(ID),
  NOMBRE         VARCHAR2(100) NOT NULL,
  APELLIDO       VARCHAR2(100),
  TELEFONO       VARCHAR2(20) NOT NULL,
  NUM_PERSONAS   NUMBER DEFAULT 1,
  CODIGO_QR      VARCHAR2(50) UNIQUE,        -- se genera solo cuando el admin confirma el pago
  ESTADO_PAGO    VARCHAR2(20) DEFAULT 'PENDIENTE' CHECK (ESTADO_PAGO IN ('PENDIENTE','CONFIRMADO')),
  FECHA_RESERVA  TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ---------------------------------------------------------
-- 4. SOLICITUDES_ALQUILER: la "bandeja de notificaciones"
--    del admin para pedidos de alquiler del espacio
-- ---------------------------------------------------------
CREATE TABLE SOLICITUDES_ALQUILER (
  ID                NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  NOMBRE            VARCHAR2(100) NOT NULL,
  TELEFONO          VARCHAR2(20) NOT NULL,
  FECHA_DESEADA     DATE NOT NULL,
  RANGO_HORA_APROX  VARCHAR2(50),     -- ej: "7pm a 10pm, aprox"
  TIPO_EVENTO       VARCHAR2(150),    -- descripción libre de qué quiere hacer
  ESTADO            VARCHAR2(20) DEFAULT 'PENDIENTE' CHECK (ESTADO IN ('PENDIENTE','CONTACTADO','CONFIRMADO','RECHAZADO')),
  EVENTO_ID         NUMBER REFERENCES EVENTOS(ID),   -- se llena solo cuando el admin confirma y crea el evento ALQUILER
  FECHA_SOLICITUD   TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- =========================================================
-- NOTA: validación de cruce de horarios al confirmar un alquiler
-- Antes de hacer UPDATE/INSERT en EVENTOS con TIPO='ALQUILER',
-- correr esta consulta desde el backend. Si devuelve > 0, hay cruce:
--
-- SELECT COUNT(*) FROM EVENTOS
-- WHERE TIPO = 'ALQUILER'
--   AND ESTADO = 'ACTIVO'
--   AND FECHA_INICIO < :nueva_fecha_fin
--   AND FECHA_FIN     > :nueva_fecha_inicio;
-- =========================================================

-- NOTA sobre seguridad: no uses el usuario ADMIN de Oracle para que
-- el backend se conecte. Crea un usuario/esquema propio de la app, ej:
--
-- CREATE USER APP_CAFEREAL IDENTIFIED BY "UnaContraseñaFuerte123!";
-- GRANT CONNECT, RESOURCE TO APP_CAFEREAL;
-- GRANT UNLIMITED TABLESPACE TO APP_CAFEREAL;
--
-- Y desde ese usuario (APP_CAFEREAL) creas estas tablas, no desde ADMIN.
