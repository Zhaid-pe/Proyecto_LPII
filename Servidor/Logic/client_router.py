import sys
import os
import json
import logging
import threading
import struct

from Controllers.auth_controller import AuthController
from Controllers.room_controller import RoomController
from Controllers.chat_controller import ChatController
from Controllers.file_controller import FileController
from Controllers.media_controller import MediaController
from Database.manager import db_manager as db

logging.basicConfig(level=logging.INFO, format="[ROUTER] %(asctime)s - %(message)s")

class ClientRouter:
    def __init__(self, sock, addr, server):
        self.sock = sock
        self.addr = addr
        self.server = server

        # Estado del cliente
        self.usuario: dict | None = None
        self.id_sala: int | None = None
        self.es_host: bool = False

        self._lock = threading.Lock()

        # Recepción de archivos en chunks
        self._file_meta: dict | None = None
        self._file_chunks: list[bytes] = []

    def _recv_exact(self, n: int) -> bytes | None:
        data = b""
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except OSError:
                return None
        return data

    def run(self):
        try:
            while True:
                header = self._recv_exact(7)
                if not header:
                    break

                tamanio, canal_bytes = struct.unpack("!I3s", header)
                canal = canal_bytes.decode("utf-8").strip()

                payload = self._recv_exact(tamanio)
                if payload is None:
                    break

                if canal == "CMD":
                    msg = json.loads(payload.decode("utf-8"))
                    self._dispatch(msg)
                elif canal == "VID":
                    MediaController.handle_raw_video(self, payload)
                elif canal == "AUD":
                    MediaController.handle_raw_audio(self, payload)

        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            self._on_disconnect()

    def send_raw_packet(self, canal: str, payload: bytes):
        with self._lock:
            try:
                header = struct.pack("!I3s", len(payload), canal.encode("utf-8")[:3])
                self.sock.sendall(header + payload)
            except OSError:
                pass

    def send(self, data: dict):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_raw_packet("CMD", raw)

    def _dispatch(self, msg: dict):
        tipo = msg.get("tipo", "")
        handlers = {
            "LOGIN_REQUEST":     AuthController.handle_login,
            "REGISTER_REQUEST":  AuthController.handle_register,
            "CREATE_ROOM":       RoomController.handle_create_room,
            "JOIN_ROOM_REQUEST": RoomController.handle_join_room,
            "ADMIT_USER":        RoomController.handle_admit_user,
            "REJECT_USER":       RoomController.handle_reject_user,
            "KICK_USER":         RoomController.handle_kick_user,
            "WAIT_USER":         RoomController.handle_wait_user,
            "LEAVE_ROOM":        RoomController.handle_leave_room,
            "CHAT_MESSAGE":      ChatController.handle_chat_message,
            "FILE_META":         FileController.handle_file_meta,
            "FILE_CHUNK":        FileController.handle_file_chunk,
            "FILE_END":          FileController.handle_file_end,
            "DOWNLOAD_FILE_REQUEST": FileController.handle_download_request,
            "CAMERA_OFF":        MediaController.handle_camera_off,
        }
        fn = handlers.get(tipo)
        if fn:
            fn(self, msg)
        else:
            logging.warning(f"Mensaje de comando desconocido: {tipo}")

    def _on_disconnect(self):
        self.cleanup_sala()
        try:
            self.sock.close()
        except OSError:
            pass
        nombre = self.usuario["nombre"] if self.usuario else str(self.addr)
        logging.info(f"Cliente desconectado: {nombre}")

    def cleanup_sala(self):
        if self.id_sala:
            if self.es_host:
                self.server.broadcast_sala(self.id_sala, {"tipo": "ROOM_CLOSED"}, excluir=self)
                db.cerrar_sala(self.id_sala)
            else:
                self.server.broadcast_sala(self.id_sala, {
                    "tipo": "USER_LEFT",
                    "id_usuario": self.usuario["id_usuario"] if self.usuario else None,
                    "nombre": self.usuario["nombre"] if self.usuario else "Desconocido",
                }, excluir=self)
            self.server.desregistrar_de_sala(self.id_sala, self)
            self.id_sala = None
            self.es_host = False

    def find_handler(self, id_usuario: int):
        with self.server.lock:
            for h in self.server.salas_activas.get(self.id_sala, []):
                if h.usuario and h.usuario["id_usuario"] == id_usuario:
                    return h
        return None

    def get_codigo_sala(self, id_sala: int) -> str:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), "..", "Database", "zoom_clone.db")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT codigo_sala FROM Salas WHERE id_sala=?", (id_sala,)).fetchone()
        conn.close()
        return row[0] if row else ""
