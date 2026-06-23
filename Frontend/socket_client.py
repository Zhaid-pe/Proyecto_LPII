"""
socket_client.py – Conexión TCP al servidor.
Recibe mensajes en un hilo secundario y los pone en una Queue
para que la GUI los consuma de forma segura.
"""

import socket
import threading
import json
import queue
import base64
import os
import logging

logging.basicConfig(level=logging.INFO, format="[CLIENT] %(asctime)s - %(message)s")

HOST = "127.0.0.1"
PORT = 9090
CHUNK_SIZE = 32768   # 32 KB por chunk de archivo
DOWNLOADS_PATH = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_PATH, exist_ok=True)


class SocketClient:
    def __init__(self):
        self.sock: socket.socket | None = None
        self.connected = False
        self.message_queue: queue.Queue = queue.Queue()
        self._buffer = b""
        self._lock = threading.Lock()

    # ── Conexión ───────────────────────────────────────────────────────────────

    def connect(self, host=HOST, port=PORT) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            t = threading.Thread(target=self._receive_loop, daemon=True)
            t.start()
            logging.info(f"Conectado al servidor {host}:{port}")
            return True
        except (ConnectionRefusedError, OSError) as e:
            logging.error(f"No se pudo conectar: {e}")
            return False

    def disconnect(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    # ── Envío ──────────────────────────────────────────────────────────────────

    def send(self, data: dict):
        with self._lock:
            if not self.connected:
                return
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8") + b"\n"
            try:
                self.sock.sendall(raw)
            except OSError as e:
                logging.error(f"Error al enviar: {e}")

    # ── Mensajes de alto nivel ─────────────────────────────────────────────────

    def login(self, correo: str, password: str):
        self.send({"tipo": "LOGIN_REQUEST", "correo": correo, "password": password})

    def register(self, nombre: str, correo: str, password: str):
        self.send({"tipo": "REGISTER_REQUEST", "nombre": nombre, "correo": correo, "password": password})

    def create_room(self, nombre_sala: str):
        self.send({"tipo": "CREATE_ROOM", "nombre_sala": nombre_sala})

    def join_room(self, codigo_sala: str):
        self.send({"tipo": "JOIN_ROOM_REQUEST", "codigo_sala": codigo_sala})

    def admit_user(self, id_usuario: int):
        self.send({"tipo": "ADMIT_USER", "id_usuario": id_usuario})

    def reject_user(self, id_usuario: int):
        self.send({"tipo": "REJECT_USER", "id_usuario": id_usuario})

    def chat_message(self, texto: str):
        self.send({"tipo": "CHAT_MESSAGE", "texto": texto})

    def leave_room(self):
        self.send({"tipo": "LEAVE_ROOM"})

    def send_file(self, filepath: str):
        """Envía un archivo al servidor en chunks."""
        nombre = os.path.basename(filepath)
        tamanio = os.path.getsize(filepath)
        self.send({"tipo": "FILE_META", "nombre_archivo": nombre, "tamanio_bytes": tamanio})
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                self.send({"tipo": "FILE_CHUNK", "data": base64.b64encode(chunk).decode("ascii")})
        self.send({"tipo": "FILE_END"})
        logging.info(f"Archivo enviado: {nombre} ({tamanio} bytes)")

    def send_camera_frame(self, frame_bytes: bytes):
        """Envía un frame JPEG comprimido como base64."""
        self.send({
            "tipo": "CAMERA_FRAME",
            "frame": base64.b64encode(frame_bytes).decode("ascii"),
        })

    # ── Recepción ──────────────────────────────────────────────────────────────

    def _receive_loop(self):
        while self.connected:
            try:
                data = self.sock.recv(65536)
                if not data:
                    break
                self._buffer += data
                while b"\n" in self._buffer:
                    line, self._buffer = self._buffer.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            self.message_queue.put(msg)
                        except json.JSONDecodeError:
                            pass
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
        self.connected = False
        self.message_queue.put({"tipo": "DISCONNECTED"})
        logging.info("Desconectado del servidor.")
