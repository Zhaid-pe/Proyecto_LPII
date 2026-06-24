"""
main_client.py  Controlador principal del cliente.
Orquesta las vistas (LoginView, DashboardView, WaitingView, RoomView)
y el SocketClient. Consume la Queue de mensajes mediante un QTimer.
"""

import sys
import os
import threading
import base64
import time
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QImage  # Importación necesaria para el manejo nativo de frames

from Frontend.socket_client import SocketClient
from Frontend.views.login_view import LoginView
from Frontend.views.dashboard_view import DashboardView
from Frontend.views.waiting_view import WaitingView
from Frontend.views.room_view import RoomView

IDX_LOGIN     = 0
IDX_DASHBOARD = 1
IDX_WAITING   = 2
IDX_ROOM      = 3


class MainClient(QMainWindow):
    # Declaramos la señal aquí afuera
    from PySide6.QtCore import Signal
    local_frame_ready = Signal(bytes)

    def __init__(self, host="127.0.0.1", port=9090):
        super().__init__()
        self.setWindowTitle("ZoomClone")
        self.setMinimumSize(1100, 680)

        self.client = SocketClient()
        self.usuario = None
        self._camera_thread = None
        self._camera_running = False
        self._current_host = host
        self._port = port
        self._last_password = ""
        self._pending_join_code = None

        # Vistas
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_view     = LoginView()
        self.dashboard_view = DashboardView()
        self.waiting_view   = WaitingView()
        self.room_view      = RoomView()  # <--- Aquí nace room_view

        self.stack.addWidget(self.login_view)
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.waiting_view)
        self.stack.addWidget(self.room_view)

        # Senales
        self.login_view.login_requested.connect(self._do_login)
        self.login_view.register_requested.connect(self._do_register)

        self.dashboard_view.create_room_requested.connect(self._do_create_room)
        self.dashboard_view.join_room_requested.connect(self._do_join_room)
        self.dashboard_view.logout_requested.connect(self._do_logout)

        self.waiting_view.cancel_requested.connect(self._do_leave)

        self.room_view.send_chat.connect(self.client.chat_message)
        self.room_view.send_file.connect(self._do_send_file)
        self.room_view.download_file.connect(self._do_request_file)
        self.room_view.leave_room.connect(self._do_leave)
        self.room_view.admit_user.connect(self.client.admit_user)
        self.room_view.reject_user.connect(self.client.reject_user)
        self.room_view.camera_toggle.connect(self._toggle_camera)

        # <--- Nuestra nueva señal, de forma segura al final de las conexiones
        self.local_frame_ready.connect(self.room_view.show_local_frame)

        # Timer poll mensajes
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_messages)
        self._timer.start(50)

    # ── Navegacion ───────────────────────────────────────────────────────────────

    def _go(self, index: int):
        self.stack.setCurrentIndex(index)

    # ── Poll mensajes ────────────────────────────────────────────────────────────

    def _poll_messages(self):
        while not self.client.message_queue.empty():
            msg = self.client.message_queue.get_nowait()
            self._handle_server_message(msg)

    def _handle_server_message(self, msg: dict):
        tipo = msg.get("tipo", "")

        if tipo == "LOGIN_RESPONSE":
            if msg["exito"]:
                self.usuario = msg["usuario"]
                self.dashboard_view.set_usuario(self.usuario)
                if self._pending_join_code:
                    code = self._pending_join_code
                    self._pending_join_code = None
                    self.client.join_room(code)
                else:
                    self._go(IDX_DASHBOARD)
            else:
                self.login_view.show_error(msg.get("error", "Credenciales invalidas"))

        elif tipo == "REGISTER_RESPONSE":
            if msg["exito"]:
                self.usuario = msg["usuario"]
                self.dashboard_view.set_usuario(self.usuario)
                self._go(IDX_DASHBOARD)
            else:
                self.login_view.show_error(msg.get("error", "Error al registrar"))

        elif tipo == "CREATE_ROOM_RESPONSE":
            if msg["exito"]:
                self.room_view.setup(msg["sala"], self.usuario, es_host=True)
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
            QMessageBox.information(self, "Acceso denegado", "El anfitrion no te admitio en la sala.")

        elif tipo == "USER_WANTS_JOIN":
            self.room_view.show_join_request(msg["id_usuario"], msg["nombre"])

        elif tipo == "USER_JOINED":
            self.room_view.add_participant(msg["nombre"])
            self.room_view.system_message(f"{msg['nombre']} se unio a la reunion")

        elif tipo == "USER_LEFT":
            self.room_view.remove_participant(msg.get("nombre", ""))
            self.room_view.system_message(f"{msg.get('nombre', 'Alguien')} salio de la reunion")

        elif tipo == "ROOM_CLOSED":
            self._go(IDX_DASHBOARD)
            QMessageBox.information(self, "Sala cerrada", "El anfitrion cerro la reunion.")

        elif tipo == "CHAT_MESSAGE":
            es_propio = (self.usuario and msg["id_usuario"] == self.usuario["id_usuario"])
            self.room_view.append_chat(msg["nombre"], msg["texto"], es_propio)

        elif tipo == "FILE_AVAILABLE":
            self.room_view.add_file(msg["nombre_archivo"], msg["remitente"])
            self.room_view.system_message(f"{msg['remitente']} compartio '{msg['nombre_archivo']}'")

        elif tipo == "CAMERA_FRAME":
            self.room_view.show_camera_frame(msg["frame"])

        elif tipo == "DISCONNECTED":
            # Si fue a propósito, no mostramos el error y reiniciamos la bandera
            if getattr(self, '_cierre_intencional', False):
                self._cierre_intencional = False
            else:
                # Si no fue a propósito, mostramos la alerta de caída real
                QMessageBox.critical(self, "Desconectado", "Se perdio la conexion con el servidor.")
            
            self._go(IDX_LOGIN)

        elif tipo == "ERROR":
            QMessageBox.warning(self, "Error del servidor", msg.get("mensaje", ""))

    # ── Acciones ─────────────────────────────────────────────────────────────────

    def _conectar_a(self, ip: str) -> bool:
        if self.client.connected and self._current_host == ip:
            return True
        self.client.disconnect()
        if not self.client.connect(ip, self._port):
            QMessageBox.critical(
                self, "Sin conexion",
                f"No se pudo conectar al servidor en {ip}:{self._port}\n\n"
                "Verifica que:\n"
                "  - El servidor este corriendo (modo Servidor o Ambos)\n"
                "  - La IP sea correcta (preguntale al anfitrion)\n"
                "  - Esten en la misma red WiFi"
            )
            return False
        self._current_host = ip
        return True

    def _do_login(self, ip: str, correo: str, password: str):
        if not self._conectar_a(ip):
            return
        self._last_password = password
        self.client.login(correo, password)

    def _do_register(self, ip: str, nombre: str, correo: str, password: str):
        if not self._conectar_a(ip):
            return
        self._last_password = password
        self.client.register(nombre, correo, password)

    def _do_create_room(self, nombre_sala: str):
        self.client.create_room(nombre_sala)

    def _do_join_room(self, ip: str, codigo: str):
        if not self._conectar_a(ip):
            return
        if self._current_host != self.login_view.get_ip():
            self._pending_join_code = codigo
            self.client.login(self.usuario["correo"], self._last_password)
        else:
            self.client.join_room(codigo)

    def _do_logout(self):
        self.usuario = None
        # Avisamos al sistema que esta desconexión es a propósito
        self._cierre_intencional = True 
        
        self.client.disconnect()
        self._go(IDX_LOGIN)

    def _do_leave(self):
        self._stop_camera()
        self.client.leave_room()
        self._go(IDX_DASHBOARD)

    def _do_send_file(self, filepath: str):
        t = threading.Thread(target=self.client.send_file, args=(filepath,), daemon=True)
        t.start()
    
    def _do_request_file(self, nombre_archivo: str):
        from PySide6.QtWidgets import QFileDialog
        import os
        import base64 # Asegúrate de que base64 esté importado arriba en tu archivo
        
        # Preguntar al usuario dónde guardar el archivo
        ruta_guardado, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo como", nombre_archivo
        )
        
        if ruta_guardado:
            # Guardamos la ruta temporalmente para usarla cuando el servidor responda
            if not hasattr(self, '_archivos_pendientes'):
                self._archivos_pendientes = {}
            self._archivos_pendientes[nombre_archivo] = ruta_guardado
            
            # Avisamos al servidor que queremos este archivo
            self.client.request_file(nombre_archivo)

    # ── Camara ────────────────────────────────────────────────────────────────────

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
                "Instala opencv-python para usar la camara:\n\npip install opencv-python"
            )
            self.room_view._reset_camera_ui()
            return

        if self._camera_thread and self._camera_thread.is_alive():
            self._camera_running = False
            self._camera_thread.join(timeout=0.3)

        self._camera_running = True
        self._camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._camera_thread.start()

    def _stop_camera(self):
        self._camera_running = False

    def _camera_loop(self):
        import cv2
        import time
        import traceback
        from PySide6.QtGui import QImage
        from PySide6.QtCore import QTimer

        print("DEBUG [Camara]: Iniciando captura de hardware...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("DEBUG [Camara]: Falla critica - No se pudo abrir VideoCapture(0)")
            QTimer.singleShot(0, lambda: self._on_camera_error("No se pudo abrir la camara."))
            return

        print("DEBUG [Camara]: Hardware abierto correctamente. Iniciando bucle...")

        try:
            while self._camera_running:
                ret, frame = cap.read()
                if not ret:
                    print("DEBUG [Camara]: OpenCV bloqueado por el sistema operativo.")
                    # Llamamos a nuestra nueva función de alerta
                    QTimer.singleShot(0, lambda: self._on_camera_error(
                        "Windows impidió la captura de video."
                    ))
                    break

                try:
                    # ---> AQUÍ ESTÁ EL CAMBIO: Invertir la imagen horizontalmente (efecto espejo) <---
                    frame = cv2.flip(frame, 1)

                    # 1. Redimensionar el frame para procesamiento estable
                    frame_small = cv2.resize(frame, (320, 240))

                    # 2. Compresión JPEG a bytes
                    _, buf = cv2.imencode(".jpg", frame_small, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_bytes = buf.tobytes()

                    # 3. Enviar a la UI local usando la Señal Segura
                    self.local_frame_ready.emit(frame_bytes)
                    
                    # 4. Enviar al socket
                    self.client.send_camera_frame(frame_bytes)

                except Exception as e:
                    # ... resto de tus excepciones ...
                    print(f"\n❌ ERROR FATAL DENTRO DEL HILO DE LA CAMARA ❌")
                    print(f"Detalle del error: {e}")
                    traceback.print_exc()
                    break

                time.sleep(0.07)
                
        finally:
            cap.release()
            print("DEBUG [Camara]: Hardware liberado y apagado.")

    def _on_camera_error(self, mensaje: str):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        # Apagamos el estado de la cámara en la interfaz por seguridad
        self._camera_running = False
        if hasattr(self, 'room_view'):
            self.room_view.btn_camera.setText("Activar camara")

        # Creamos un cuadro de diálogo elegante
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Error de Cámara")
        msg_box.setText(mensaje)
        msg_box.setInformativeText("Si la luz de tu cámara encendió pero no hay video, es muy probable que Windows esté bloqueando el acceso por privacidad.\n\n¿Deseas abrir la configuración de privacidad de Windows para solucionarlo?")
        
        # Botones personalizados
        btn_abrir_ajustes = msg_box.addButton("Abrir Ajustes de Privacidad", QMessageBox.AcceptRole)
        btn_cancelar = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_abrir_ajustes)

        msg_box.exec()

        # Si el usuario hace clic en abrir ajustes, lanzamos el comando a Windows
        if msg_box.clickedButton() == btn_abrir_ajustes:
            # Este comando abre mágicamente la pestaña exacta de permisos de cámara en Windows 10 y 11
            QDesktopServices.openUrl(QUrl("ms-settings:privacy-webcam"))

    def closeEvent(self, event):
        self._stop_camera()
        if hasattr(self, 'client') and self.client:
            self.client.disconnect()
        event.accept()
        os._exit(0)

