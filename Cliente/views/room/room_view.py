"""
room_view.py  Pantalla principal de la reunion.
Paneles: Camara | Chat (con archivos integrados)
"""

import os
import base64

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFrame,
    QListWidget, QListWidgetItem,
    QFileDialog, QSplitter, QMessageBox,QGridLayout,
    QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QByteArray
from PySide6.QtGui import QFont, QPixmap, QImage

DOWNLOADS_PATH = os.path.join(os.path.dirname(__file__), "..", "downloads")
os.makedirs(DOWNLOADS_PATH, exist_ok=True)


class RoomView(QWidget):
    send_chat     = Signal(str)
    send_file     = Signal(str)
    download_file = Signal(str)
    leave_room    = Signal()
    admit_user    = Signal(int)
    reject_user   = Signal(int)
    kick_user_requested = Signal(int)
    wait_user_requested = Signal(int)
    camera_toggle = Signal(bool)
    mic_toggle    = Signal(bool)  # Señal para el micrófono añadida

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estados internos de los controles
        self.camara_activa = False
        self.mic_activo = False
        self._pending_requests = {} # Inicialización interna para evitar errores en solicitudes
        self.video_feeds = {}

        self.current_page = 1
        self.max_per_page = 6
        self.room_members = ["Tú"] 
        self.member_widgets = {}

        # Instanciar los nuevos botones redondos con emojis
        self.btn_mic = QPushButton("🎙️")
        self.btn_camera = QPushButton("📷")

        # Ajustar fuente (tamaño del icono) y tamaño cuadrado de los botones
        font = self.btn_camera.font()
        font.setPointSize(16)
        self.btn_mic.setFont(font)
        self.btn_camera.setFont(font)

        self.btn_mic.setFixedSize(50, 50)
        self.btn_camera.setFixedSize(50, 50)

        # Estilo Rojo (Apagado / Meet Style)
        self.ESTILO_OFF = """
            QPushButton { background-color: #ea4335; color: white; border-radius: 25px; border: none; }
            QPushButton:hover { background-color: #d33426; }
        """
        # Estilo Gris (Prendido / Activo)
        self.ESTILO_ON = """
            QPushButton { background-color: #3c4043; color: white; border-radius: 25px; border: none; }
            QPushButton:hover { background-color: #5f6368; }
        """

        # Aplicar estilos iniciales (Apagados por defecto)
        self.btn_mic.setStyleSheet(self.ESTILO_OFF)
        self.btn_camera.setStyleSheet(self.ESTILO_OFF)

        # Conectar eventos de clic
        self.btn_mic.clicked.connect(self._on_mic_clicked)
        self.btn_camera.clicked.connect(self._on_camera_clicked)

        # ¡CRUCIAL! Volver a llamar a la construcción de la interfaz completa
        self._build_ui()

    def setup(self, sala: dict, usuario: dict, es_host: bool):
        self.sala_info = sala
        self.usuario = usuario
        self.es_host = es_host
        nombre_sala = sala.get("nombre_sala", "Sala")
        codigo = sala.get("codigo_sala", "")
        self.lbl_titulo.setText(f"Reunion: {nombre_sala}")
        self.lbl_codigo.setText(f"Codigo: {codigo}")
        
        # Limpiar datos previos
        self.list_participants.clear()
        self.list_requests.clear()
        self._pending_requests.clear()
        self.chat_display.clear()
        self.list_files.clear()
        self.room_members.clear()
        for w in self.member_widgets.values():
            w.deleteLater()
        self.member_widgets.clear()
        self._render_current_page()
        
        self._system_message(f"Conectado a '{nombre_sala}' - Codigo: {codigo}")
        if es_host:
            self._system_message("Eres el anfitrion. Los participantes veran una sala de espera.")

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #12121f; color: #e0e0e0; font-family: Arial; font-size: 13px; }
            QFrame#panel {
                background: #1a1a2e; border: 1px solid #2a2a40; border-radius: 10px;
            }
            QLineEdit {
                background: #232336; border: 1px solid #333; border-radius: 6px;
                padding: 6px 10px; color: #e0e0e0;
            }
            QLineEdit:focus { border-color: #2D8CFF; }
            QTextEdit {
                background: #181828; border: none; color: #e0e0e0; font-size: 13px;
            }
            QListWidget {
                background: #181828; border: none; color: #ccc;
            }
            QPushButton#primary {
                background: #2D8CFF; color: white; border-radius: 6px;
                font-weight: bold; padding: 6px 14px;
            }
            QPushButton#primary:hover { background: #1a7ae0; }
            QPushButton#danger {
                background: #dc3545; color: white; border-radius: 6px;
                font-weight: bold; padding: 6px 14px;
            }
            QPushButton#danger:hover { background: #b02a37; }
            QPushButton#success {
                background: #28a745; color: white; border-radius: 6px;
                padding: 4px 10px; font-size: 12px;
            }
            QPushButton#reject {
                background: #dc3545; color: white; border-radius: 6px;
                padding: 4px 10px; font-size: 12px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())
        
        # ❌ ELIMINA o comenta el self._render_current_page() que estaba aquí

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("QSplitter::handle { background: #2a2a40; }")
        splitter.addWidget(self._build_camera_panel())
        splitter.addWidget(self._build_chat_panel())
        splitter.setSizes([560, 440])

        root.addWidget(splitter)

        # ✅ PONLO AQUÍ AL FINAL:
        self._render_current_page()

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet("background:#0d0d1a; border-bottom:1px solid #222;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)

        self.lbl_titulo = QLabel("Reunion")
        self.lbl_titulo.setFont(QFont("Arial", 15, QFont.Bold))
        self.lbl_titulo.setStyleSheet("color:#2D8CFF;")

        self.lbl_codigo = QLabel("")
        self.lbl_codigo.setStyleSheet("color:#666; font-size:12px; margin-left:12px;")

        btn_leave = QPushButton("Salir de la reunion")
        btn_leave.setObjectName("danger")
        btn_leave.setFixedHeight(34)
        btn_leave.clicked.connect(self._on_leave)

        lay.addWidget(self.lbl_titulo)
        lay.addWidget(self.lbl_codigo)
        lay.addStretch()
        lay.addWidget(btn_leave)
        return bar

    # ── Panel Camara ─────────────────────────────────────────────────────────────

    def _build_camera_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- 1. NUEVA ZONA DE VIDEO (MOSAICO DINÁMICO) ---
        self.video_area_widget = QWidget()
        self.video_area_widget.setStyleSheet("background-color: #111; border-radius: 8px;") 
        self.video_grid = QGridLayout(self.video_area_widget)
        self.video_grid.setSpacing(10)
        self.video_grid.setContentsMargins(10, 10, 10, 10)
        
        # Agregamos el contenedor del mosaico al panel central y le damos stretch=1 
        # para que ocupe todo el espacio sobrante.
        layout.addWidget(self.video_area_widget, stretch=1)

        # --- 1.5 CONTROLES DE PAGINACIÓN ---
        self.pag_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<")
        self.btn_next = QPushButton(">")
        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.setAlignment(Qt.AlignCenter)

        estilo_btn = "background: #3c4043; color: white; border-radius: 4px; padding: 4px;"
        self.btn_prev.setStyleSheet(estilo_btn)
        self.btn_next.setStyleSheet(estilo_btn)
        self.btn_prev.setFixedSize(30, 30)
        self.btn_next.setFixedSize(30, 30)

        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)

        self.pag_layout.addStretch()
        self.pag_layout.addWidget(self.btn_prev)
        self.pag_layout.addWidget(self.lbl_page)
        self.pag_layout.addWidget(self.btn_next)
        self.pag_layout.addStretch()

        layout.addLayout(self.pag_layout)
        
        # --- 2. CONTROLES DE LA REUNIÓN (MIC / CAM) ---
        ctrl = QHBoxLayout()
        ctrl.addStretch()
        ctrl.addWidget(self.btn_mic)
        ctrl.addWidget(self.btn_camera)
        ctrl.addStretch()
        
        layout.addLayout(ctrl)

        # --- 3. PANEL DE SOLICITUDES DE INGRESO (WAITING ROOM) ---
        self.frame_requests = QFrame()
        self.frame_requests.setStyleSheet("background:#161625; border-radius:8px;")
        req_layout = QVBoxLayout(self.frame_requests)
        req_layout.setContentsMargins(10, 8, 10, 8)
        
        lbl_req = QLabel("Solicitudes de ingreso")
        lbl_req.setStyleSheet("font-weight:bold; color:#aaa; font-size:12px;")
        req_layout.addWidget(lbl_req)
        
        self.list_requests = QListWidget()
        self.list_requests.setMaximumHeight(150)
        req_layout.addWidget(self.list_requests)
        
        self.frame_requests.setVisible(False)
        layout.addWidget(self.frame_requests)

        # --- 4. LISTA DE PARTICIPANTES ---
        lbl_participantes = QLabel("Participantes")
        lbl_participantes.setStyleSheet("font-weight:bold; color:#aaa; font-size:12px;")
        layout.addWidget(lbl_participantes)
        
        self.list_participants = QListWidget()
        self.list_participants.setMaximumHeight(120)
        self.list_participants.setStyleSheet("background:#0d0d1a; border-radius:6px; color:#aaa;")
        layout.addWidget(self.list_participants)

        return panel

    # ── Panel Chat ───────────────────────────────────────────────────────────────

    def _build_chat_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Chat")
        header.setFont(QFont("Arial", 13, QFont.Bold))
        layout.addWidget(header)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Acordeon de archivos
        self.files_header = QPushButton("Archivos compartidos  v")
        self.files_header.setCheckable(True)
        self.files_header.setChecked(False)
        self.files_header.setStyleSheet("""
            QPushButton {
                background: #1e1e36; border: 1px solid #2a2a50;
                border-radius: 6px; color: #aaa; font-size: 12px;
                padding: 5px 10px; text-align: left;
            }
            QPushButton:checked { color: #2D8CFF; border-color: #2D8CFF; }
            QPushButton:hover { background: #25253a; }
        """)
        self.files_header.clicked.connect(self._toggle_files_list)
        layout.addWidget(self.files_header)

        self.list_files = QListWidget()
        self.list_files.setMaximumHeight(110)
        self.list_files.setVisible(False)
        self.list_files.setStyleSheet(
            "background:#0d0d1a; border:1px solid #2a2a40; border-radius:6px; color:#ccc; font-size:12px;"
        )
        layout.addWidget(self.list_files)

        # --- BARRA DE PROGRESO (OCULTA POR DEFECTO) ---
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        prog_lay = QVBoxLayout(self.progress_frame)
        prog_lay.setContentsMargins(0, 5, 0, 5)

        self.lbl_progress = QLabel("Progreso...")
        self.lbl_progress.setStyleSheet("color:#aaa; font-size:11px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #333; border-radius: 4px; background: #222; }
            QProgressBar::chunk { background: #2D8CFF; border-radius: 4px; }
        """)

        prog_lay.addWidget(self.lbl_progress)
        prog_lay.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_frame) # Se añade encima de la caja de texto
        # ----------------------------------------------

        # Barra de entrada (Esto ya lo tienes)
        input_row = QHBoxLayout()

        # Barra de entrada
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Escribe un mensaje...")
        self.chat_input.setFixedHeight(38)
        self.chat_input.returnPressed.connect(self._on_send_chat)

        btn_attach = QPushButton("@")
        btn_attach.setToolTip("Compartir archivo")
        btn_attach.setFixedSize(38, 38)
        btn_attach.setStyleSheet("""
            QPushButton { background: #232336; border: 1px solid #333;
                          border-radius: 6px; font-size: 16px; color: #aaa; }
            QPushButton:hover { background: #2D8CFF; color: white; border-color: #2D8CFF; }
        """)
        btn_attach.clicked.connect(self._on_share_file)

        btn_send = QPushButton("Enviar")
        btn_send.setObjectName("primary")
        btn_send.setFixedSize(70, 38)
        btn_send.clicked.connect(self._on_send_chat)

        input_row.addWidget(self.chat_input)
        input_row.addWidget(btn_attach)
        input_row.addWidget(btn_send)
        layout.addLayout(input_row)

        return panel

    def _toggle_files_list(self, checked: bool):
        self.list_files.setVisible(checked)
        count = self.list_files.count()
        arrow = "^" if checked else "v"
        label = f"Archivos compartidos ({count})  {arrow}" if count else f"Archivos compartidos  {arrow}"
        self.files_header.setText(label)

    # ── Slots internos ───────────────────────────────────────────────────────────

    def _on_leave(self):
        reply = QMessageBox.question(
            self, "Salir", "Seguro que quieres salir de la reunion?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.leave_room.emit()

    def _on_send_chat(self):
        texto = self.chat_input.text().strip()
        if texto:
            self.send_chat.emit(texto)
            self.chat_input.clear()

    def _on_share_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
        if path:
            self.send_file.emit(path)

    def _reset_camera_ui(self):
        """Apaga la interfaz de la cámara local eliminando tu cuadro del mosaico."""
        # En lugar de borrar la imagen de un QLabel fijo, simplemente
        # le decimos al mosaico que elimine la pantalla llamada "Tú"
        self.remove_video_feed("Tú")

    # ── API publica ──────────────────────────────────────────────────────────────

    def append_chat(self, nombre: str, texto: str, es_propio: bool = False):
        color = "#2D8CFF" if es_propio else "#28a745"
        self.chat_display.append(
            f'<span style="color:{color};font-weight:bold;">{nombre}</span>: {texto}'
        )

    def system_message(self, texto: str):
        self._system_message(texto)

    def _system_message(self, texto: str):
        self.chat_display.append(
            f'<span style="color:#555;font-style:italic;">-- {texto} --</span>'
        )

    def add_participant(self, id_usuario: int, nombre: str):
        item_widget = QWidget()
        row = QHBoxLayout(item_widget)
        row.setContentsMargins(4, 2, 4, 2)
        lbl = QLabel(f"  {nombre}")
        lbl.setStyleSheet("color:#aaa;")
        row.addWidget(lbl)
        row.addStretch()

        if self.es_host:
            btn_wait = QPushButton("🕒")
            btn_wait.setFixedSize(24, 24)
            btn_wait.setToolTip("Enviar a sala de espera")
            btn_wait.setStyleSheet("background: #f0ad4e; color: white; border-radius: 4px; border: none;")
            btn_wait.clicked.connect(lambda: self.wait_user_requested.emit(id_usuario))
            
            btn_kick = QPushButton("❌")
            btn_kick.setFixedSize(24, 24)
            btn_kick.setToolTip("Expulsar")
            btn_kick.setStyleSheet("background: #dc3545; color: white; border-radius: 4px; border: none;")
            btn_kick.clicked.connect(lambda: self.kick_user_requested.emit(id_usuario))
            
            row.addWidget(btn_wait)
            row.addWidget(btn_kick)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        item.setData(Qt.UserRole, id_usuario)
        item.setData(Qt.UserRole + 1, nombre)
        self.list_participants.addItem(item)
        self.list_participants.setItemWidget(item, item_widget)

        # Agregarlo a la cuadrícula visual si no existe
        if nombre not in self.room_members:
            self.room_members.append(nombre)
            self._render_current_page()

    def remove_participant(self, nombre: str):
        for i in range(self.list_participants.count()):
            item = self.list_participants.item(i)
            if item.data(Qt.UserRole + 1) == nombre or (item.text() and nombre in item.text()):
                self.list_participants.takeItem(i)
                break
        # Quitarlo de la cuadrícula visual
        if nombre in self.room_members:
            self.room_members.remove(nombre)
            if nombre in self.member_widgets:
                widget = self.member_widgets.pop(nombre)
                widget.deleteLater()
            self._render_current_page()

    def add_file(self, nombre_archivo: str, remitente: str):
        item_widget = QWidget()
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(8, 2, 8, 2)
        
        # Etiqueta con el nombre del archivo
        lbl = QLabel(f"{nombre_archivo}  (por {remitente})")
        lbl.setStyleSheet("color:#ccc; font-size:11px;")
        
        # Botón de descarga
        btn_download = QPushButton("⬇️")
        btn_download.setFixedSize(24, 24)
        btn_download.setToolTip("Descargar archivo")
        btn_download.setStyleSheet("""
            QPushButton { background: #2D8CFF; color: white; border-radius: 4px; border: none; }
            QPushButton:hover { background: #1a7ae0; }
        """)
        # Al hacer clic, emitimos el nombre del archivo
        btn_download.clicked.connect(lambda: self.download_file.emit(nombre_archivo))
        
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(btn_download)
        
        # Añadir a la lista
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self.list_files.addItem(item)
        self.list_files.setItemWidget(item, item_widget)
        
        # Actualizar el contador del acordeón
        count = self.list_files.count()
        checked = self.files_header.isChecked()
        arrow = "^" if checked else "v"
        self.files_header.setText(f"Archivos compartidos ({count})  {arrow}")

    def show_join_request(self, id_usuario: int, nombre: str):
        self._pending_requests[id_usuario] = nombre
        self.frame_requests.setVisible(True)

        item_widget = QWidget()
        row = QHBoxLayout(item_widget)
        row.setContentsMargins(4, 2, 4, 2)
        lbl = QLabel(f"{nombre}")
        lbl.setStyleSheet("color:#ddd;")
        btn_admit = QPushButton("Admitir")
        btn_admit.setObjectName("success")
        btn_reject = QPushButton("Rechazar")
        btn_reject.setObjectName("reject")

        btn_admit.clicked.connect(lambda: self._admit(id_usuario))
        btn_reject.clicked.connect(lambda: self._reject(id_usuario))

        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(btn_admit)
        row.addWidget(btn_reject)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        item.setData(Qt.UserRole, id_usuario)
        self.list_requests.addItem(item)
        self.list_requests.setItemWidget(item, item_widget)

    def _remove_request_item(self, id_usuario: int):
        for i in range(self.list_requests.count()):
            item = self.list_requests.item(i)
            if item.data(Qt.UserRole) == id_usuario:
                self.list_requests.takeItem(i)
                break
        if self.list_requests.count() == 0:
            self.frame_requests.setVisible(False)
        self._pending_requests.pop(id_usuario, None)

    def _admit(self, id_usuario: int):
        self._remove_request_item(id_usuario)
        self.admit_user.emit(id_usuario)

    def _reject(self, id_usuario: int):
        self._remove_request_item(id_usuario)
        self.reject_user.emit(id_usuario)

    # ── Manejo de Video (Mosaico Paginado Zoom-Style) ───────────────────────────

    def _get_or_create_widget(self, nombre: str):
        """Crea una caja gris por defecto si la persona no tiene cámara encendida"""
        if nombre not in self.member_widgets:
            lbl = QLabel(nombre)
            lbl.setStyleSheet("background: #222; color: #aaa; border: 1px solid #444; border-radius: 8px; font-size: 16px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.member_widgets[nombre] = lbl
        return self.member_widgets[nombre]

    def _render_current_page(self):
        """Actualiza la pantalla para mostrar solo a las personas de la página actual"""
        
        # --- ESCUDO DE SEGURIDAD ---
        if not hasattr(self, 'lbl_page'):
            return
        # ---------------------------

        total_pages = max(1, (len(self.room_members) + self.max_per_page - 1) // self.max_per_page)
        if self.current_page > total_pages:
            self.current_page = total_pages

        self.lbl_page.setText(f"{self.current_page} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

        # --- FORMA SEGURA DE LIMPIAR LA CUADRÍCULA ---
        for i in reversed(range(self.video_grid.count())):
            widget = self.video_grid.itemAt(i).widget()
            if widget:
                self.video_grid.removeWidget(widget)
                widget.hide()  # Lo ocultamos en lugar de destruirlo

        # Calcular quiénes tocan en esta página
        start_idx = (self.current_page - 1) * self.max_per_page
        end_idx = start_idx + self.max_per_page
        visible_members = self.room_members[start_idx:end_idx]

        # Pintarlos en la cuadrícula (2 columnas)
        for idx, nombre in enumerate(visible_members):
            widget = self._get_or_create_widget(nombre)
            widget.show()  # Lo volvemos a hacer visible
            row = idx // 2
            col = idx % 2
            self.video_grid.addWidget(widget, row, col)

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        self.current_page += 1
        self._render_current_page()

    def show_camera_frame(self, frame_b64: str, nombre: str = "Remoto"):
        """Recibe un frame remoto (base64) y lo manda al mosaico."""
        try:
            raw = base64.b64decode(frame_b64)
            self._update_mosaic_frame(nombre, raw)
        except Exception as e:
            print(f"DEBUG [UI]: Error al mostrar imagen remota: {e}")

    def show_local_frame(self, frame_bytes: bytes):
        """Recibe el frame de tu cámara web local y lo pone en el mosaico."""
        try:
            self._update_mosaic_frame("Tú", frame_bytes)
        except Exception as e:
            print(f"DEBUG [UI]: Error al mostrar imagen local en mosaico: {e}")

    def _update_mosaic_frame(self, nombre: str, frame_data: bytes):
        """Pinta la imagen en la cuadrícula sobre su caja correspondiente."""
        if nombre not in self.room_members:
            self.room_members.append(nombre)
            self._render_current_page()

        lbl = self._get_or_create_widget(nombre)
        img = QImage()
        img.loadFromData(frame_data)
        if not img.isNull():
            w = max(lbl.width(), 320)
            h = max(lbl.height(), 240)
            pixmap = QPixmap.fromImage(img).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl.setPixmap(pixmap)

    def _reset_camera_ui(self):
        """Cuando apagas tu cámara, vuelve a mostrar la caja con tu nombre"""
        if "Tú" in self.member_widgets:
            lbl = self.member_widgets["Tú"]
            lbl.clear()
            lbl.setText("Tú")

    def load_history(self, mensajes: list):
        for m in mensajes:
            self.append_chat(m["nombre"], m["texto"])

    # ── Manejo de Clics de los Nuevos Botones ──────────────────────────────────────

    def _on_camera_clicked(self):
        self.camara_activa = not self.camara_activa
        
        if self.camara_activa:
            self.btn_camera.setStyleSheet(self.ESTILO_ON)
        else:
            self._reset_camera_ui()
            self.btn_camera.setStyleSheet(self.ESTILO_OFF) # <-- Faltaba esta línea
            
        self.camera_toggle.emit(self.camara_activa)

    def _on_mic_clicked(self):
        self.mic_activo = not self.mic_activo
        
        if self.mic_activo:
            self.btn_mic.setStyleSheet(self.ESTILO_ON)
        else:
            self.btn_mic.setStyleSheet(self.ESTILO_OFF)
            
        self.mic_toggle.emit(self.mic_activo)

    def update_progress(self, nombre: str, porcentaje: int, es_subida: bool):
        self.progress_frame.setVisible(True)
        accion = "Subiendo" if es_subida else "Descargando"
        self.lbl_progress.setText(f"{accion}: {nombre} ({porcentaje}%)")
        self.progress_bar.setValue(porcentaje)
        
        # Si llega a 100%, ocultamos la barra después de 2 segundos
        if porcentaje >= 100:
            QTimer.singleShot(2000, lambda: self.progress_frame.setVisible(False))