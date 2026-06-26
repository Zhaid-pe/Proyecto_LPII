"""
socket_client.py Conexión TCP al servidor con separación de canales.
Recibe paquetes mediante cabeceras fijas de 7 bytes [Largo(4B)][Canal(3B)].
"""

import socket
import threading
import json
import queue
import base64
import os
import logging
import struct

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
        self._lock = threading.Lock()

    # ── Conexión ───────────────────────────────────────────────────────────────

    def connect(self, host=HOST, port=PORT) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            t = threading.Thread(target=self._receive_loop, daemon=True)
            t.start()
            logging.info(f"Conectado al servidor {host}:{port} con canales multiplexados")
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

    # ── Envío Multiplexado (La Clave) ──────────────────────────────────────────

    def send_packet(self, canal: str, payload: bytes):
        """Envía datos anteponiendo un header fijo de 7 bytes: [Tamaño(4B)][Canal(3B)]"""
        with self._lock:
            if not self.connected or not self.sock:
                return
            try:
                # '!I3s' = Big-endian, Entero de 4 bytes, String de 3 bytes
                header = struct.pack("!I3s", len(payload), canal.encode("utf-8")[:3])
                self.sock.sendall(header + payload)
            except OSError as e:
                logging.error(f"Error al enviar por canal {canal}: {e}")

    def send(self, data: dict):
        """Mantiene compatibilidad con tus métodos existentes de comandos/chat"""
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_packet("CMD", raw)

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

    def send_file(self, filepath: str, progress_callback=None): # <-- Añadimos el callback
        nombre = os.path.basename(filepath)
        tamanio = os.path.getsize(filepath)
        self.send({"tipo": "FILE_META", "nombre_archivo": nombre, "tamanio_bytes": tamanio})
        
        enviado = 0 # <-- Contador de bytes
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                self.send({"tipo": "FILE_CHUNK", "data": base64.b64encode(chunk).decode("ascii")})
                
                # --- NUEVA LÓGICA DE PROGRESO ---
                enviado += len(chunk)
                if progress_callback:
                    progress_callback(nombre, enviado, tamanio)
                # --------------------------------
                    
        self.send({"tipo": "FILE_END"})
        logging.info(f"Archivo enviado: {nombre} ({tamanio} bytes)")

    def request_file(self, nombre_archivo: str):
        """Pide al servidor que nos envíe un archivo específico"""
        self.send({
            "tipo": "DOWNLOAD_FILE_REQUEST", 
            "nombre_archivo": nombre_archivo
        })

    def send_camera_frame(self, frame_bytes: bytes):
        """CANAL VIDEO: Envía bytes binarios puros de la cámara instantáneamente"""
        self.send_packet("VID", frame_bytes)

    def send_audio_frame(self, audio_bytes: bytes):
        """CANAL AUDIO: Envía bytes binarios puros del micrófono sin latencia"""
        self.send_packet("AUD", audio_bytes)

    # ── Recepción Estructurada ─────────────────────────────────────────────────

    def _recv_exact(self, n: int) -> bytes | None:
        """Asegura la lectura exacta de N bytes del stream TCP"""
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

    def _receive_loop(self):
        while self.connected:
            try:
                # 1. Leer los 7 bytes de la cabecera fija
                header = self._recv_exact(7)
                if not header:
                    break

                tamanio, canal_bytes = struct.unpack("!I3s", header)
                canal = canal_bytes.decode("utf-8").strip()

                # 2. Leer el cuerpo del paquete exacto
                payload = self._recv_exact(tamanio)
                if payload is None:
                    break

                # 3. Enrutamiento por canales seguros
                if canal == "CMD":
                    msg = json.loads(payload.decode("utf-8"))
                    self.message_queue.put(msg)
                    
                elif canal == "VID":
                    # El servidor nos manda: [4B UserID] + [Bytes del Frame]
                    id_usuario = int.from_bytes(payload[:4], byteorder="big")
                    frame_raw = payload[4:]
                    # Lo codificamos a b64 al recibir solo si tu GUI vieja lo necesita así
                    frame_b64 = base64.b64encode(frame_raw).decode("ascii")
                    
                    self.message_queue.put({
                        "tipo": "CAMERA_FRAME",
                        "id_usuario": id_usuario,
                        "frame": frame_b64
                    })
                    
                elif canal == "AUD":
                    # El servidor nos manda: [4B UserID] + [Bytes de Audio]
                    id_usuario = int.from_bytes(payload[:4], byteorder="big")
                    audio_raw = payload[4:]
                    audio_b64 = base64.b64encode(audio_raw).decode("ascii")
                    
                    self.message_queue.put({
                        "tipo": "AUDIO_FRAME",
                        "id_usuario": id_usuario,
                        "audio": audio_b64
                    })

            except Exception as e:
                logging.error(f"Error en loop de recepción: {e}")
                break

        self.connected = False
        self.message_queue.put({"tipo": "DISCONNECTED"})
        logging.info("Desconectado del servidor.")