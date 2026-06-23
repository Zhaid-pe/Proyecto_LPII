"""
main_client.py – Controlador principal del cliente.
Orquesta las vistas (LoginView, DashboardView, WaitingView, RoomView)
y el SocketClient. Consume la Queue de mensajes mediante un QTimer.
"""

import threading
import base64

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import QTimer

from Frontend.socket_client import SocketClient
from Frontend.views.login_view import LoginView
from Frontend.views.dashboard_view import DashboardView
from Frontend.views.waiting_view import WaitingView
from Frontend.views.room_view import RoomView

# Índices en el QStackedWidget
IDX_LOGIN     = 0
IDX_DASHBOARD = 1
IDX_WAITING   = 2
IDX_ROOM      = 3


class MainClient(QMainWindow):
    def __init__(self, host="127.0.0.1", port=9090):
        super().__init__()
        self.setWindowTitle("ZoomClone")
        self.setMinimumSize(1100, 680)

        self.client = SocketClient()
        self.usuario: dict | None = None
        self._camera_thread: threading.Thread | None = None
        self._camera_running = False

        # ── Vistas ──────────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_view    = LoginView()
        self.dashboard_view = DashboardView()
        self.waiting_view  = WaitingView()
        self.room_view     = RoomView()

        self.stack.addWidget(self.login_view)     # 0
        self.stack.addWidget(self.dashboard_view) # 1
        self.stack.addWidget(self.waiting_view)   # 2
        self.stack.addWidget(self.room_view)      # 3

        # ── Conectar señales ─────────────────────────────────────────────────────
        self.login_view.login_requested.connect(self._do_login)
        self.login_view.register_requested.connect(self._do_register)

        self.dashboard_view.create_room_requested.connect(self._do_create_room)
        self.dashboard_view.join_room_requested.connect(self._do_join_room)
        self.dashboard_view.logout_requested.connect(self._do_logout)

        self.waiting_view.cancel_requested.connect(self._do_leave)

        self.room_view.send_chat.connect(self.client.chat_message)
        self.room_view.send_file.connect(self._do_send_file)
        self.room_view.leave_room.connect(self._do_leave)
        self.room_view.admit_user.connect(self.client.admit_user)
        self.room_view.reject_user.connect(self.client.reject_user)
        self.room_view.camera_toggle.connect(self._toggle_camera)

        # ── Timer de mensajes ────────────────────────────────────────────────────
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_messages)
        self._timer.start(50)   # cada 50 ms

        # ── Conectar al servidor ─────────────────────────────────────────────────
        if not self.client.connect(host, port):
            QMessageBox.critical(
                self, "Sin conexión",
                f"No se pudo conectar al servidor {host}:{port}.\n"
                "Asegúrate de que el servidor esté corriendo."
            )

    # ── Navegación ───────────────────────────────────────────────────────────────

    def _go(self, index: int):
        self.stack.setCurrentIndex(index)

    # ── Poll de mensajes del servidor ────────────────────────────────────────────

    def _poll_messages(self):
        while not self.client.message_queue.empty():
            msg = self.client.message_queue.get_nowait()
            self._handle_server_message(msg)

    def _handle_server_message(self, msg: dict):
        tipo = msg.get("tipo", "")

        # ── Autenticación
        if tipo == "LOGIN_RESPONSE":
            if msg["exito"]:
                self.usuario = msg["usuario"]
                self.dashboard_view.set_usuario(self.usuario)
                self._go(IDX_DASHBOARD)
            else:
                self.login_view.show_error(msg.get("error", "Error desconocido"))

        elif tipo == "REGISTER_RESPONSE":
            if msg["exito"]:
                self.usuario = msg["usuario"]
                self.dashboard_view.set_usuario(self.usuario)
                self._go(IDX_DASHBOARD)
            else:
                self.login_view.show_error(msg.get("error", "Error desconocido"))

        # ── Salas
        elif tipo == "CREATE_ROOM_RESPONSE":
            if msg["exito"]:
                sala = msg["sala"]
                self.room_view.setup(sala, self.usuario, es_host=True)
                self._go(IDX_ROOM)

        elif tipo == "JOIN_ROOM_RESPONSE":
            if msg["exito"]:
                sala = msg["sala"]
                if msg["estado"] == "pendiente":
                    self.waiting_view.set_info(sala.get("nombre_sala", "Sala"), sala.get("codigo_sala", ""))
                    self._go(IDX_WAITING)
                else:
                    self.room_view.setup(sala, self.usuario, es_host=False)
                    self._go(IDX_ROOM)
            else:
                QMessageBox.warning(self, "Error", msg.get("error", "No se pudo unir"))

        elif tipo == "ADMITTED_TO_ROOM":
            sala = msg.get("sala", {})
            self.room_view.setup(sala, self.usuario, es_host=False)
            mensajes = msg.get("mensajes_previos", [])
            if mensajes:
                self.room_view.load_history(mensajes)
            self._go(IDX_ROOM)

        elif tipo == "REJECTED_FROM_ROOM":
            self._go(IDX_DASHBOARD)
            QMessageBox.information(self, "Acceso denegado", "El anfitrión no te admitió en la sala.")

        # ── Solicitudes (solo host ve esto)
        elif tipo == "USER_WANTS_JOIN":
            self.room_view.show_join_request(msg["id_usuario"], msg["nombre"])

        # ── Participantes
        elif tipo == "USER_JOINED":
            self.room_view.add_participant(msg["nombre"])
            self.room_view.system_message(f"{msg['nombre']} se unió a la reunión")

        elif tipo == "USER_LEFT":
            self.room_view.remove_participant(msg.get("nombre", ""))
            self.room_view.system_message(f"{msg.get('nombre', 'Alguien')} salió de la reunión")

        elif tipo == "ROOM_CLOSED":
            self._go(IDX_DASHBOARD)
            QMessageBox.information(self, "Sala cerrada", "El anfitrión cerró la reunión.")

        # ── Chat
        elif tipo == "CHAT_MESSAGE":
            es_propio = (self.usuario and msg["id_usuario"] == self.usuario["id_usuario"])
            self.room_view.append_chat(msg["nombre"], msg["texto"], es_propio)

        # ── Archivos
        elif tipo == "FILE_AVAILABLE":
            self.room_view.add_file(msg["nombre_archivo"], msg["remitente"])
            self.room_view.system_message(
                f"{msg['remitente']} compartió «{msg['nombre_archivo']}»"
            )

        # ── Cámara
        elif tipo == "CAMERA_FRAME":
            self.room_view.show_camera_frame(msg["frame"])

        # ── Desconexión
        elif tipo == "DISCONNECTED":
            QMessageBox.critical(self, "Desconectado", "Se perdió la conexión con el servidor.")
            self._go(IDX_LOGIN)

        elif tipo == "ERROR":
            QMessageBox.warning(self, "Error del servidor", msg.get("mensaje", ""))

    # ── Acciones del usuario ─────────────────────────────────────────────────────

    def _do_login(self, correo: str, password: str):
        self.client.login(correo, password)

    def _do_register(self, nombre: str, correo: str, password: str):
        self.client.register(nombre, correo, password)

    def _do_create_room(self, nombre_sala: str):
        self.client.create_room(nombre_sala)

    def _do_join_room(self, codigo: str):
        self.client.join_room(codigo)

    def _do_logout(self):
        self.usuario = None
        self._go(IDX_LOGIN)

    def _do_leave(self):
        self._stop_camera()
        self.client.leave_room()
        self._go(IDX_DASHBOARD)

    def _do_send_file(self, filepath: str):
        t = threading.Thread(target=self.client.send_file, args=(filepath,), daemon=True)
        t.start()

    # ── Cámara ───────────────────────────────────────────────────────────────────

    def _toggle_camera(self, active: bool):
        if active:
            self._start_camera()
        else:
            self._stop_camera()

    def _start_camera(self):
        try:
            import cv2
        except ImportError:
            QMessageBox.warning(
                self, "OpenCV no disponible",
                "Instala opencv-python para usar la cámara:\n\npip install opencv-python"
            )
            return

        self._camera_running = True
        self._camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._camera_thread.start()

    def _stop_camera(self):
        self._camera_running = False

    def _camera_loop(self):
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return
        try:
            while self._camera_running:
                ret, frame = cap.read()
                if not ret:
                    break
                # Redimensionar y comprimir
                frame_small = cv2.resize(frame, (320, 240))
                _, buf = cv2.imencode(".jpg", frame_small, [cv2.IMWRITE_JPEG_QUALITY, 60])
                frame_bytes = buf.tobytes()
                frame_b64 = base64.b64encode(frame_bytes).decode("ascii")

                # Actualizar vista local (necesita invocación en hilo GUI)
                QTimer.singleShot(0, lambda f=frame_b64: self.room_view.show_local_frame(f))

                # Enviar al servidor
                self.client.send_camera_frame(frame_bytes)

                import time
                time.sleep(0.1)   # ~10 FPS
        finally:
            cap.release()
