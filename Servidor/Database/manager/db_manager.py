"""
db_manager.py  Capa de acceso a datos (SQLite)
Todas las operaciones de BD pasan por este módulo.
"""

import sqlite3
import hashlib
import os
import random
import string

CORRIENTE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.dirname(CORRIENTE_DIR)

SCHEMA_PATH = os.path.join(DATABASE_DIR, "schema.sql")
DB_PATH = os.path.join(DATABASE_DIR, "zoom_clone.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea las tablas si no existen."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = _get_conn()
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print("[DB] Base de datos inicializada correctamente.")


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Usuarios ──────────────────────────────────────────────────────────────────

def registrar_usuario(nombre: str, correo: str, password: str):
    """Devuelve el id_usuario recién creado o None si el correo ya existe."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO Usuarios (nombre, correo, password_hash) VALUES (?, ?, ?)",
            (nombre, correo, _hash_password(password))
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def validar_usuario(correo: str, password: str):
    """Devuelve dict con datos del usuario o None si las credenciales son inválidas."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id_usuario, nombre, correo FROM Usuarios WHERE correo=? AND password_hash=?",
        (correo, _hash_password(password))
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def obtener_usuario_por_id(id_usuario: int):
    conn = _get_conn()
    row = conn.execute(
        "SELECT id_usuario, nombre, correo FROM Usuarios WHERE id_usuario=?",
        (id_usuario,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Salas ─────────────────────────────────────────────────────────────────────

def _generar_codigo(longitud=6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=longitud))


def crear_sala(nombre_sala: str, id_host: int):
    """Devuelve el dict de la sala creada."""
    codigo = _generar_codigo()
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO Salas (codigo_sala, nombre_sala, id_host) VALUES (?, ?, ?)",
        (codigo, nombre_sala, id_host)
    )
    conn.commit()
    id_sala = cur.lastrowid
    conn.close()
    return {"id_sala": id_sala, "codigo_sala": codigo, "nombre_sala": nombre_sala, "id_host": id_host}


def obtener_sala_por_codigo(codigo_sala: str):
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM Salas WHERE codigo_sala=? AND estado='activa'",
        (codigo_sala,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def cerrar_sala(id_sala: int):
    conn = _get_conn()
    conn.execute("UPDATE Salas SET estado='cerrada' WHERE id_sala=?", (id_sala,))
    conn.commit()
    conn.close()


# ── Participantes ─────────────────────────────────────────────────────────────

def agregar_participante(id_sala: int, id_usuario: int, estado: str = "pendiente"):
    conn = _get_conn()
    # Evitar duplicados
    existing = conn.execute(
        "SELECT id FROM ParticipantesSala WHERE id_sala=? AND id_usuario=?",
        (id_sala, id_usuario)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO ParticipantesSala (id_sala, id_usuario, estado) VALUES (?, ?, ?)",
            (id_sala, id_usuario, estado)
        )
        conn.commit()
    conn.close()


def actualizar_estado_participante(id_sala: int, id_usuario: int, nuevo_estado: str):
    conn = _get_conn()
    conn.execute(
        "UPDATE ParticipantesSala SET estado=? WHERE id_sala=? AND id_usuario=?",
        (nuevo_estado, id_sala, id_usuario)
    )
    conn.commit()
    conn.close()


def obtener_participantes_admitidos(id_sala: int):
    conn = _get_conn()
    rows = conn.execute(
        """SELECT u.id_usuario, u.nombre, u.correo
           FROM ParticipantesSala p
           JOIN Usuarios u ON p.id_usuario = u.id_usuario
           WHERE p.id_sala=? AND p.estado='admitido'""",
        (id_sala,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Mensajes ──────────────────────────────────────────────────────────────────

def guardar_mensaje(id_sala: int, id_usuario: int, texto: str):
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO Mensajes (id_sala, id_usuario, texto) VALUES (?, ?, ?)",
        (id_sala, id_usuario, texto)
    )
    conn.commit()
    id_msg = cur.lastrowid
    conn.close()
    return id_msg


def obtener_mensajes_sala(id_sala: int, limit: int = 50):
    conn = _get_conn()
    rows = conn.execute(
        """SELECT m.id_mensaje, m.texto, m.timestamp, u.nombre
           FROM Mensajes m
           JOIN Usuarios u ON m.id_usuario = u.id_usuario
           WHERE m.id_sala=?
           ORDER BY m.timestamp ASC
           LIMIT ?""",
        (id_sala, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Archivos ──────────────────────────────────────────────────────────────────

def registrar_archivo(id_sala: int, id_usuario: int, nombre: str, ruta: str, tamanio: int):
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO ArchivosCompartidos (id_sala, id_usuario, nombre_archivo, ruta_servidor, tamanio_bytes) VALUES (?, ?, ?, ?, ?)",
        (id_sala, id_usuario, nombre, ruta, tamanio)
    )
    conn.commit()
    id_archivo = cur.lastrowid
    conn.close()
    return id_archivo


def obtener_archivos_sala(id_sala: int):
    conn = _get_conn()
    rows = conn.execute(
        """SELECT a.id_archivo, a.nombre_archivo, a.tamanio_bytes, a.timestamp, u.nombre
           FROM ArchivosCompartidos a
           JOIN Usuarios u ON a.id_usuario = u.id_usuario
           WHERE a.id_sala=?
           ORDER BY a.timestamp ASC""",
        (id_sala,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
