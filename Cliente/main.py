import sys
import os
import threading
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

# Asegurar que la ruta base esté en sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Imports de la interfaz de usuario (UI)
from UI.main_window import MainWindow, IDX_LOGIN, IDX_DASHBOARD

# Imports de la logica de negocio (Logic)
from Logic.network_client import SocketClient
from Logic.camera_controller import CameraController
from Logic.message_router import MessageRouter

class AppMediator:
    """Orquestador que une la UI con la lógica de red y cámara (Mediator Pattern)."""
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # Inicializar vistas y controladores
        self.window = MainWindow()
        self.client = SocketClient()
        self.camera_controller = CameraController(self.client)
        self.message_router = MessageRouter(self.client, self.window)

        self._current_host = "127.0.0.1"
        self._port = 9090
        
        self._setup_signals()
        
    def _setup_signals(self):
        self.window.go_back_requested.connect(self._do_go_back)
        # Conexiones desde UI hacia Lógica de Red (Login/Salas)
        self.window.login_view.login_requested.connect(self._do_login)
        self.window.login_view.register_requested.connect(self._do_register)
        self.window.dashboard_view.create_room_requested.connect(self.client.create_room)
        self.window.dashboard_view.join_room_requested.connect(self.client.join_room)
        self.window.room_view.send_chat.connect(self.client.chat_message)
        self.window.room_view.admit_user.connect(self.client.admit_user)
        self.window.room_view.reject_user.connect(self.client.reject_user)
        self.window.room_view.kick_user_requested.connect(self.client.kick_user)
        self.window.room_view.wait_user_requested.connect(self.client.wait_user)
        
        # File transfers
        self.window.room_view.send_file.connect(self._do_send_file)
        self.window.room_view.download_file.connect(self._do_request_file)
        
        # Room lifecycle
        self.window.leave_room_requested.connect(self._do_leave)
        self.window.logout_requested.connect(self._do_logout)

        # Cámara (UI <-> Camera Controller)
        self.window.room_view.camera_toggle.connect(self._toggle_camera)
        self.camera_controller.local_frame_ready.connect(self.window.room_view.show_local_frame)
        self.camera_controller.camera_error.connect(self._on_camera_error)

    def _do_go_back(self):
        if hasattr(self, 'on_back') and self.on_back:
            self.on_back()

    def run(self):
        self.window.show()
        self.message_router.start()
        sys.exit(self.app.exec())

    def _conectar_a(self, ip: str) -> bool:
        if self.client.connected and self._current_host == ip:
            return True
        self.client.disconnect()
        if not self.client.connect(ip, self._port):
            self.window.show_critical(
                "Sin conexion",
                f"No se pudo conectar al servidor en {ip}:{self._port}\n\n"
                "Verifica que:\n"
                "  - El servidor este corriendo\n"
                "  - La IP sea correcta\n"
                "  - Esten en la misma red"
            )
            return False
        self._current_host = ip
        return True

    def _do_login(self, ip: str, correo: str, password: str):
        if not self._conectar_a(ip): return
        self.client.login(correo, password)

    def _do_register(self, ip: str, nombre: str, correo: str, password: str):
        if not self._conectar_a(ip): return
        self.client.register(nombre, correo, password)

    def _do_logout(self):
        self.message_router.usuario = None
        self.window._cierre_intencional = True
        self.client.disconnect()
        self.window.go_to(IDX_LOGIN)

    def _do_leave(self):
        if self.message_router.usuario:
            self.camera_controller.toggle_camera(False, self.message_router.usuario.get("nombre", "Usuario"))
        self.client.leave_room()
        self.window.go_to(IDX_DASHBOARD)

    def _do_send_file(self, filepath: str):
        def _progress_cb(nombre, enviado, total):
            porcentaje = int((enviado / total) * 100) if total > 0 else 100
            self.window.room_view.update_progress(nombre, porcentaje, True)
            
        t = threading.Thread(target=self.client.send_file, args=(filepath, _progress_cb), daemon=True)
        t.start()
        
    def _do_request_file(self, nombre_archivo: str):
        from PySide6.QtWidgets import QFileDialog
        ruta_guardado, _ = QFileDialog.getSaveFileName(self.window, "Guardar archivo como", nombre_archivo)
        if ruta_guardado:
            self.message_router.prepare_download(nombre_archivo, ruta_guardado)

    def _toggle_camera(self, active: bool):
        if not self.message_router.usuario: return
        self.camera_controller.toggle_camera(active, self.message_router.usuario.get("nombre", "Usuario"))
        if not active:
            self.window.room_view._reset_camera_ui()

    def _on_camera_error(self, mensaje: str):
        self.camera_controller._camera_running = False
        self.window.room_view.btn_camera.setText("Activar camara")

        msg_box = QMessageBox(self.window)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Error de Cámara")
        msg_box.setText(mensaje)
        msg_box.setInformativeText("¿Deseas abrir la configuración de privacidad de Windows?")
        
        btn_abrir_ajustes = msg_box.addButton("Abrir Ajustes", QMessageBox.AcceptRole)
        msg_box.addButton("Cancelar", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_abrir_ajustes)
        msg_box.exec()

        if msg_box.clickedButton() == btn_abrir_ajustes:
            QDesktopServices.openUrl(QUrl("ms-settings:privacy-webcam"))

if __name__ == "__main__":
    mediator = AppMediator()
    mediator.run()
