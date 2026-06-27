import threading
import time
import traceback
from PySide6.QtCore import QObject, Signal

class CameraController(QObject):
    # Signals para conectar con la UI
    local_frame_ready = Signal(bytes)
    camera_error = Signal(str)

    def __init__(self, network_client):
        super().__init__()
        self.network_client = network_client
        self._camera_thread = None
        self._camera_running = False

    def toggle_camera(self, active: bool, username: str):
        if active:
            self._start_camera()
        else:
            self._stop_camera()
            self.network_client.send({
                "tipo": "CAMERA_OFF",
                "remitente": username
            })

    def _start_camera(self):
        try:
            import cv2
        except ImportError:
            self.camera_error.emit("Instala opencv-python para usar la camara:\n\npip install opencv-python")
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
        print("DEBUG [Camara]: Iniciando captura de hardware...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("DEBUG [Camara]: Falla critica - No se pudo abrir VideoCapture(0)")
            self.camera_error.emit("No se pudo abrir la camara.")
            return

        print("DEBUG [Camara]: Hardware abierto correctamente. Iniciando bucle...")

        try:
            while self._camera_running:
                ret, frame = cap.read()
                if not ret:
                    print("DEBUG [Camara]: OpenCV bloqueado por el sistema operativo.")
                    self.camera_error.emit("Windows impidió la captura de video.")
                    break

                try:
                    frame = cv2.flip(frame, 1)
                    frame_small = cv2.resize(frame, (320, 240))
                    _, buf = cv2.imencode(".jpg", frame_small, [cv2.IMWRITE_JPEG_QUALITY, 40])
                    frame_bytes = buf.tobytes()

                    # Emitir el frame a la UI
                    self.local_frame_ready.emit(frame_bytes)
                    # Enviar por socket
                    self.network_client.send_camera_frame(frame_bytes)

                except Exception as e:
                    print(f"\n❌ ERROR FATAL DENTRO DEL HILO DE LA CAMARA ❌")
                    print(f"Detalle del error: {e}")
                    traceback.print_exc()
                    break

                time.sleep(0.07)
                
        finally:
            cap.release()
            print("DEBUG [Camara]: Hardware liberado y apagado.")
