"""
client_handler.py Procesa el protocolo multiplexado por cliente.
Separa el flujo en canales de comandos (CMD), Video (VID) y Audio (AUD).
"""

import sys
import os
import json
import base64
import logging
import threading
import struct

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Servidor.Database.manager import db_manager as db
from Servidor.socket_server.socket_server import SocketServer

STORAGE_PATH = os.path.join(os.path.dirname(__file__), "files_storage")
os.makedirs(STORAGE_PATH, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="[HANDLER] %(asctime)s - %(message)s")


class ClientHandler:
    def __init__(self, sock, addr, server: SocketServer):
        self.sock = sock
        self.addr = addr
        self.server = server

        # Estado del cliente
        self.usuario: dict | None = None   # {"id_usuario": ..., "nombre": ..., "correo": ...}
        self.id_sala: int | None = None
        self.es_host: bool = False

        self._lock = threading.Lock()

        # Recepción de archivos en chunks
        self._file_meta: dict | None = None
        self._file_chunks: list[bytes] = []

    # ── Loop de recepción Estructurado ─────────────────────────────────────────

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
                # 1. Leer el Header (7 bytes)
                header = self._recv_exact(7)
                if not header:
                    break

                tamanio, canal_bytes = struct.unpack("!I3s", header)
                canal = canal_bytes.decode("utf-8").strip()

                # 2. Leer el Payload exacto
                payload = self._recv_exact(tamanio)
                if payload is None:
                    break

                # 3. Separación de Canales en tiempo real
                if canal == "CMD":
                    msg = json.loads(payload.decode("utf-8"))
                    self._dispatch(msg)
                elif canal == "VID":
                    self._handle_raw_video(payload)
                elif canal == "AUD":
                    self._handle_raw_audio(payload)

        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            self._on_disconnect()

    def send_raw_packet(self, canal: str, payload: bytes):
        """Envía un paquete crudo directamente por un canal específico"""
        with self._lock:
            try:
                header = struct.pack("!I3s", len(payload), canal.encode("utf-8")[:3])
                self.sock.sendall(header + payload)
            except OSError:
                pass

    def send(self, data: dict):
        """Envía comandos JSON por el canal prioritario 'CMD'"""
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_raw_packet("CMD", raw)

    # ── Dispatcher de Comandos (Canal 'CMD') ───────────────────────────────────

    def _dispatch(self, msg: dict):
        tipo = msg.get("tipo", "")
        handlers = {
            "LOGIN_REQUEST":     self._handle_login,
            "REGISTER_REQUEST":  self._handle_register,
            "CREATE_ROOM":       self._handle_create_room,
            "JOIN_ROOM_REQUEST": self._handle_join_room,
            "ADMIT_USER":        self._handle_admit_user,
            "REJECT_USER":       self._handle_reject_user,
            "KICK_USER":         self._handle_kick_user,
            "WAIT_USER":         self._handle_wait_user,
            "CHAT_MESSAGE":      self._handle_chat_message,
            "FILE_META":         self._handle_file_meta,
            "FILE_CHUNK":        self._handle_file_chunk,
            "FILE_END":          self._handle_file_end,
            "LEAVE_ROOM":        self._handle_leave_room,
            "DOWNLOAD_FILE_REQUEST": self._handle_download_request,
            "CAMERA_OFF":        self._handle_camera_off,
        }
        fn = handlers.get(tipo)
        if fn:
            fn(msg)
        else:
            logging.warning(f"Mensaje de comando desconocido: {tipo}")

    # ── Autenticación ──────────────────────────────────────────────────────────

    def _handle_login(self, msg):
        usuario = db.validar_usuario(msg.get("correo", ""), msg.get("password", ""))
        if usuario:
            self.usuario = usuario
            self.send({"tipo": "LOGIN_RESPONSE", "exito": True, "usuario": usuario})
            logging.info(f"Login exitoso: {usuario['correo']}")
        else:
            self.send({"tipo": "LOGIN_RESPONSE", "exito": False, "error": "Credenciales inválidas"})

    def _handle_register(self, msg):
        id_u = db.registrar_usuario(msg.get("nombre", ""), msg.get("correo", ""), msg.get("password", ""))
        if id_u:
            usuario = db.obtener_usuario_por_id(id_u)
            self.usuario = usuario
            self.send({"tipo": "REGISTER_RESPONSE", "exito": True, "usuario": usuario})
        else:
            self.send({"tipo": "REGISTER_RESPONSE", "exito": False, "error": "El correo ya está registrado"})

    # ── Salas ──────────────────────────────────────────────────────────────────

    def _handle_create_room(self, msg):
        if not self.usuario:
            return self.send({"tipo": "ERROR", "mensaje": "No autenticado"})
        sala = db.crear_sala(msg.get("nombre_sala", "Mi Sala"), self.usuario["id_usuario"])
        db.agregar_participante(sala["id_sala"], self.usuario["id_usuario"], "admitido")
        self.id_sala = sala["id_sala"]
        self.es_host = True
        self.server.registrar_en_sala(self.id_sala, self)
        self.send({"tipo": "CREATE_ROOM_RESPONSE", "exito": True, "sala": sala})
        logging.info(f"Sala creada: {sala['codigo_sala']} por {self.usuario['nombre']}")

    def _handle_join_room(self, msg):
        if not self.usuario:
            return self.send({"tipo": "ERROR", "mensaje": "No autenticado"})
        sala = db.obtener_sala_por_codigo(msg.get("codigo_sala", ""))
        if not sala:
            return self.send({"tipo": "JOIN_ROOM_RESPONSE", "exito": False, "error": "Sala no encontrada"})

        db.agregar_participante(sala["id_sala"], self.usuario["id_usuario"], "pendiente")
        self.id_sala = sala["id_sala"]
        self.es_host = False
        self.server.registrar_en_sala(self.id_sala, self)

        host_handler = self.server.get_host_handler(sala["id_sala"])
        if host_handler:
            host_handler.send({
                "tipo": "USER_WANTS_JOIN",
                "id_usuario": self.usuario["id_usuario"],
                "nombre": self.usuario["nombre"],
                "correo": self.usuario["correo"],
            })

        self.send({"tipo": "JOIN_ROOM_RESPONSE", "exito": True, "estado": "pendiente", "sala": sala})
        logging.info(f"{self.usuario['nombre']} solicita entrar a {sala['codigo_sala']}")

    def _handle_admit_user(self, msg):
        if not self.es_host or not self.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(self.id_sala, id_target, "admitido")

        target = self._find_handler(id_target)
        if target:
            sala_info = db.obtener_sala_por_codigo(self._get_codigo_sala(self.id_sala))
            target.es_host = False
            mensajes_previos = db.obtener_mensajes_sala(self.id_sala)
            participantes_previos = db.obtener_participantes_admitidos(self.id_sala)
            
            target.send({
                "tipo": "ADMITTED_TO_ROOM",
                "sala": sala_info,
                "mensajes_previos": mensajes_previos,
                "participantes_previos": participantes_previos,
            })

        usuario = db.obtener_usuario_por_id(id_target)
        self.server.broadcast_sala(self.id_sala, {
            "tipo": "USER_JOINED",
            "id_usuario": id_target,
            "nombre": usuario["nombre"] if usuario else "Desconocido",
        })

    def _handle_reject_user(self, msg):
        if not self.es_host or not self.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(self.id_sala, id_target, "rechazado")
        target = self._find_handler(id_target)
        if target:
            target.send({"tipo": "REJECTED_FROM_ROOM"})
            self.server.desregistrar_de_sala(self.id_sala, target)

    def _handle_kick_user(self, msg):
        if not self.es_host or not self.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(self.id_sala, id_target, "expulsado")
        target = self._find_handler(id_target)
        if target:
            target.send({"tipo": "KICKED_FROM_ROOM"})
            self.server.desregistrar_de_sala(self.id_sala, target)
            self.server.broadcast_sala(self.id_sala, {
                "tipo": "USER_LEFT",
                "nombre": target.usuario["nombre"] if target.usuario else "Desconocido"
            })

    def _handle_wait_user(self, msg):
        if not self.es_host or not self.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(self.id_sala, id_target, "pendiente")
        target = self._find_handler(id_target)
        if target:
            target.send({"tipo": "SENT_TO_WAITING_ROOM"})
            self.server.desregistrar_de_sala(self.id_sala, target)
            self.server.broadcast_sala(self.id_sala, {
                "tipo": "USER_LEFT",
                "nombre": target.usuario["nombre"] if target.usuario else "Desconocido"
            })
            # Re-enviar la solicitud al host
            self.send({
                "tipo": "USER_WANTS_JOIN",
                "id_usuario": target.usuario["id_usuario"],
                "nombre": target.usuario["nombre"],
                "correo": target.usuario["correo"],
            })

    # ── Chat ───────────────────────────────────────────────────────────────────

    def _handle_chat_message(self, msg):
        if not self.usuario or not self.id_sala:
            return
        texto = msg.get("texto", "").strip()
        if not texto:
            return
        db.guardar_mensaje(self.id_sala, self.usuario["id_usuario"], texto)
        self.server.broadcast_sala(self.id_sala, {
            "tipo": "CHAT_MESSAGE",
            "id_usuario": self.usuario["id_usuario"],
            "nombre": self.usuario["nombre"],
            "texto": texto,
        })

    # ── Archivos (chunked) ─────────────────────────────────────────────────────

    def _handle_file_meta(self, msg):
        self._file_meta = msg
        self._file_chunks = []
        logging.info(f"Recibiendo archivo: {msg.get('nombre_archivo')}")

    def _handle_file_chunk(self, msg):
        chunk_b64 = msg.get("data", "")
        self._file_chunks.append(base64.b64decode(chunk_b64))

    def _handle_file_end(self, msg):
        if not self._file_meta or not self.usuario or not self.id_sala:
            return
        nombre = self._file_meta.get("nombre_archivo", "archivo.bin")
        ruta = os.path.join(STORAGE_PATH, f"{self.id_sala}_{nombre}")
        data_completa = b"".join(self._file_chunks)
        with open(ruta, "wb") as f:
            f.write(data_completa)

        id_archivo = db.registrar_archivo(
            self.id_sala, self.usuario["id_usuario"],
            nombre, ruta, len(data_completa)
        )
        logging.info(f"Archivo guardado: {nombre} ({len(data_completa)} bytes)")

        self.server.broadcast_sala(self.id_sala, {
            "tipo": "FILE_AVAILABLE",
            "id_archivo": id_archivo,
            "nombre_archivo": nombre,
            "tamanio_bytes": len(data_completa),
            "remitente": self.usuario["nombre"],
        })
        self._file_meta = None
        self._file_chunks = []

    # ── Redirección de Video y Audio Crudo (Ultra Rápido) ──────────────────────

    def _handle_raw_video(self, frame_bytes):
        """Retransmite los bytes de video inyectando el ID de quién lo envió"""
        if not self.usuario or not self.id_sala:
            return
        
        # Preparamos un sub-header de 15 bytes para que el cliente sepa de quién es este video
        user_name_bytes = self.usuario["nombre"][:15].encode("utf-8").ljust(15, b"\0")
        paquete_transmision = user_name_bytes + frame_bytes

        # Hacemos bypass manual por la sala en binario puro
        with self.server.lock:
            for handler in self.server.salas_activas.get(self.id_sala, []):
                if handler != self:
                    handler.send_raw_packet("VID", paquete_transmision)

    def _handle_raw_audio(self, audio_bytes):
        """Retransmite los bytes de audio inyectando el ID de quién lo envió"""
        if not self.usuario or not self.id_sala:
            return
        
        user_name_bytes = self.usuario["nombre"][:15].encode("utf-8").ljust(15, b"\0")
        paquete_transmision = user_name_bytes + audio_bytes

        with self.server.lock:
            for handler in self.server.salas_activas.get(self.id_sala, []):
                if handler != self:
                    handler.send_raw_packet("AUD", paquete_transmision)

    # ── Desconexión ────────────────────────────────────────────────────────────

    def _handle_leave_room(self, msg):
        self._cleanup_sala()

    def _on_disconnect(self):
        self._cleanup_sala()
        try:
            self.sock.close()
        except OSError:
            pass
        nombre = self.usuario["nombre"] if self.usuario else str(self.addr)
        logging.info(f"Cliente desconectado: {nombre}")

    def _cleanup_sala(self):
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

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _find_handler(self, id_usuario: int):
        with self.server.lock:
            for h in self.server.salas_activas.get(self.id_sala, []):
                if h.usuario and h.usuario["id_usuario"] == id_usuario:
                    return h
        return None

    def _get_codigo_sala(self, id_sala: int) -> str:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), "..", "Database", "zoom_clone.db")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT codigo_sala FROM Salas WHERE id_sala=?", (id_sala,)).fetchone()
        conn.close()
        return row[0] if row else ""

    def _handle_download_request(self, msg):
        nombre_archivo = msg.get("nombre_archivo")
        if not nombre_archivo or not self.id_sala: 
            return
            
        ruta = os.path.join(STORAGE_PATH, f"{self.id_sala}_{nombre_archivo}")
        
        if not os.path.exists(ruta):
            self.send({"tipo": "ERROR", "mensaje": f"El archivo {nombre_archivo} no existe en el servidor."})
            return
            
        # Leer el archivo y enviarlo por el canal de comandos (CMD)
        try:
            with open(ruta, "rb") as f:
                while True:
                    chunk = f.read(32768) # 32 KB por chunk
                    if not chunk: 
                        break
                    
                    self.send({
                        "tipo": "DOWNLOAD_CHUNK", 
                        "nombre_archivo": nombre_archivo, 
                        "data": base64.b64encode(chunk).decode("ascii")
                    })
                    
            # Avisamos que terminó de enviar
            self.send({"tipo": "DOWNLOAD_END", "nombre_archivo": nombre_archivo})
            logging.info(f"Archivo enviado a cliente: {nombre_archivo}")
            
        except Exception as e:
            self.send({"tipo": "ERROR", "mensaje": f"Error al enviar archivo: {e}"})

    def _handle_camera_off(self, msg):
        # Verificamos que el usuario esté en una sala y reenviamos el mensaje intacto
        if hasattr(self, 'id_sala') and self.id_sala:
            self.server.broadcast_sala(self.id_sala, msg, excluir=self)