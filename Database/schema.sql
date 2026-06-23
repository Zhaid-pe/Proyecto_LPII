-- =============================================
-- Esquema de Base de Datos - Prototipo Zoom
-- =============================================

CREATE TABLE IF NOT EXISTS Usuarios (
    id_usuario   INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT    NOT NULL,
    correo       TEXT    NOT NULL UNIQUE,
    password_hash TEXT   NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Salas (
    id_sala      INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_sala  TEXT    NOT NULL UNIQUE,
    nombre_sala  TEXT    NOT NULL,
    id_host      INTEGER NOT NULL,
    estado       TEXT    DEFAULT 'activa',   -- activa | cerrada
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_host) REFERENCES Usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS ParticipantesSala (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sala      INTEGER NOT NULL,
    id_usuario   INTEGER NOT NULL,
    estado       TEXT    DEFAULT 'pendiente', -- pendiente | admitido | rechazado
    fecha_ingreso DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_sala)    REFERENCES Salas(id_sala),
    FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS Mensajes (
    id_mensaje   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sala      INTEGER NOT NULL,
    id_usuario   INTEGER NOT NULL,
    texto        TEXT    NOT NULL,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_sala)    REFERENCES Salas(id_sala),
    FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS ArchivosCompartidos (
    id_archivo   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sala      INTEGER NOT NULL,
    id_usuario   INTEGER NOT NULL,
    nombre_archivo TEXT  NOT NULL,
    ruta_servidor  TEXT  NOT NULL,
    tamanio_bytes  INTEGER,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_sala)    REFERENCES Salas(id_sala),
    FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS SolicitudesSala (
    id_solicitud INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sala      INTEGER NOT NULL,
    id_usuario   INTEGER NOT NULL,
    estado       TEXT    DEFAULT 'pendiente', -- pendiente | aprobada | rechazada
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_sala)    REFERENCES Salas(id_sala),
    FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
);
