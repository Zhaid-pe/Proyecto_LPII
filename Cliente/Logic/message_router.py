import base64
from PySide6.QtCore import QObject, QTimer, Signal

class MessageRouter(QObject):
    # Definimos señales si necesitamos notificar algo directo a Main o UI de forma especial
    # Sin embargo, como el MessageRouter es el Controlador de la UI, manipulará
    # la main_window y sus sub-vistas directamente.

    def __init__(self, network_client, main_window):
        super().__init__()
        self.client = network_client
        self.window = main_window
        
        self.usuario = None
        self._pending_join_code = None
        self._archivos_pendientes = {}
        self._descargas_en_progreso = {}
        self._archivos_sala_tamanio = {}

        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_messages)

    def start(self):
        self._timer.start(50)
        
    def stop(self):
        self._timer.stop()

    def set_pending_join_code(self, code):
        self._pending_join_code = code

    def prepare_download(self, file_name, file_path):
        self._archivos_pendientes[file_name] = file_path
        self._descargas_en_progreso[file_name] = b""
        self.client.request_file(file_name)

    def _poll_messages(self):
        while not self.client.message_queue.empty():
            msg = self.client.message_queue.get_nowait()
            self._handle_server_message(msg)

    def _handle_server_message(self, msg: dict):
        from UI.main_window import IDX_DASHBOARD, IDX_WAITING, IDX_ROOM, IDX_LOGIN
        tipo = msg.get("tipo", "")

        if tipo == "LOGIN_RESPONSE":
            if msg["exito"]:
                self.usuario = msg["usuario"]
                self.window.dashboard_view.set_usuario(self.usuario)
                if self._pending_join_code:
                    code = self._pending_join_code
                    self._pending_join_code = None
                    self.client.join_room(code)
                else:
                    self.window.go_to(IDX_DASHBOARD)
            else:
                self.window.login_view.show_error(msg.get("error", "Credenciales invalidas"))

        elif tipo == "REGISTER_RESPONSE":
            if msg["exito"]:
                self.usuario = msg["usuario"]
                self.window.dashboard_view.set_usuario(self.usuario)
                self.window.go_to(IDX_DASHBOARD)
            else:
                self.window.login_view.show_error(msg.get("error", "Error al registrar"))

        elif tipo == "CREATE_ROOM_RESPONSE":
            if msg["exito"]:
                self.window.room_view.setup(msg["sala"], self.usuario, es_host=True)
                self.window.go_to(IDX_ROOM)

        elif tipo == "JOIN_ROOM_RESPONSE":
            if msg["exito"]:
                sala = msg["sala"]
                if msg["estado"] == "pendiente":
                    self.window.waiting_view.set_info(sala.get("nombre_sala", "Sala"), sala.get("codigo_sala", ""))
                    self.window.go_to(IDX_WAITING)
                else:
                    self.window.room_view.setup(sala, self.usuario, es_host=False)
                    self.window.go_to(IDX_ROOM)
            else:
                self.window.show_error("Error", msg.get("error", "No se pudo unir"))

        elif tipo == "ADMITTED_TO_ROOM":
            sala = msg.get("sala", {})
            self.window.room_view.setup(sala, self.usuario, es_host=False)
            mensajes = msg.get("mensajes_previos", [])
            if mensajes:
                self.window.room_view.load_history(mensajes)
            participantes = msg.get("participantes_previos", [])
            for p in participantes:
                self.window.room_view.add_participant(p.get("id_usuario", 0), p.get("nombre", "Desconocido"))
            self.window.go_to(IDX_ROOM)

        elif tipo == "REJECTED_FROM_ROOM":
            self.window.go_to(IDX_DASHBOARD)
            QTimer.singleShot(0, lambda: self.window.show_error(
                "Acceso denegado", "El anfitrión no te admitió en la sala.\nHas sido devuelto al menú principal."
            ))

        elif tipo == "KICKED_FROM_ROOM":
            self.window.go_to(IDX_DASHBOARD)
            QTimer.singleShot(0, lambda: self.window.show_error(
                "Expulsado", "Has sido expulsado de la sala por el anfitrión."
            ))

        elif tipo == "SENT_TO_WAITING_ROOM":
            self.window.go_to(IDX_WAITING)
            QTimer.singleShot(0, lambda: self.window.show_info(
                "Sala de espera", "El anfitrión te ha devuelto a la sala de espera.\nEspera a ser admitido de nuevo."
            ))

        elif tipo == "USER_WANTS_JOIN":
            self.window.room_view.show_join_request(msg["id_usuario"], msg["nombre"])

        elif tipo == "USER_JOINED":
            self.window.room_view.add_participant(msg.get("id_usuario", 0), msg["nombre"])
            self.window.room_view.system_message(f"{msg['nombre']} se unio a la reunion")

        elif tipo == "ROOM_CLOSED":
            self.window.go_to(IDX_DASHBOARD)
            self.window.show_info("Sala cerrada", "El anfitrion cerro la reunion.")

        elif tipo == "CHAT_MESSAGE":
            es_propio = (self.usuario and msg["id_usuario"] == self.usuario["id_usuario"])
            self.window.room_view.append_chat(msg["nombre"], msg["texto"], es_propio)

        elif tipo == "FILE_AVAILABLE":
            self.window.room_view.add_file(msg["nombre_archivo"], msg["remitente"])
            self.window.room_view.system_message(f"{msg['remitente']} compartio '{msg['nombre_archivo']}'")
            self._archivos_sala_tamanio[msg["nombre_archivo"]] = msg.get("tamanio_bytes", 1)

        elif tipo == "CAMERA_FRAME":
            self.window.room_view.show_camera_frame(msg["frame"], msg.get("remitente", "Remoto"))

        elif tipo == "DISCONNECTED":
            if getattr(self.window, '_cierre_intencional', False):
                self.window._cierre_intencional = False
            else:
                self.window.show_critical("Desconectado", "Se perdio la conexion con el servidor.")
            self.window.go_to(IDX_LOGIN)

        elif tipo == "ERROR":
            self.window.show_error("Error del servidor", msg.get("mensaje", ""))
        
        elif tipo == "DOWNLOAD_CHUNK":
            nombre = msg.get("nombre_archivo")
            if nombre in self._descargas_en_progreso:
                chunk_bytes = base64.b64decode(msg["data"])
                self._descargas_en_progreso[nombre] += chunk_bytes
                
                recibido = len(self._descargas_en_progreso[nombre])
                total = self._archivos_sala_tamanio.get(nombre, recibido)
                porcentaje = int((recibido / total) * 100) if total > 0 else 100
                self.window.room_view.update_progress(nombre, porcentaje, False)

        elif tipo == "DOWNLOAD_END":
            nombre = msg.get("nombre_archivo")
            if nombre in self._archivos_pendientes and nombre in self._descargas_en_progreso:
                ruta = self._archivos_pendientes[nombre]
                data = self._descargas_en_progreso[nombre]
                try:
                    with open(ruta, "wb") as f:
                        f.write(data)
                    self.window.show_info("Descarga exitosa", f"Archivo guardado en:\n{ruta}")
                except Exception as e:
                    self.window.show_error("Error", f"No se pudo guardar el archivo:\n{e}")
                
                del self._archivos_pendientes[nombre]
                del self._descargas_en_progreso[nombre]

        elif tipo == "CAMERA_OFF":
            quien_apago = msg.get("remitente")
            if quien_apago in self.window.room_view.member_widgets:
                label_remoto = self.window.room_view.member_widgets[quien_apago]
                label_remoto.clear() 
                label_remoto.setText(quien_apago)

        elif tipo == "USER_LEFT":
            nombre_usuario_que_salio = msg.get("nombre")
            if nombre_usuario_que_salio:
                self.window.room_view.remove_participant(nombre_usuario_que_salio)
