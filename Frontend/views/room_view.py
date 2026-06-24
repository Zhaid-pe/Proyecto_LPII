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
    QFileDialog, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QByteArray
from PySide6.QtGui import QFont, QPixmap, QImage

DOWNLOADS_PATH = os.path.join(os.path.dirname(__file__), "..", "downloads")
os.makedirs(DOWNLOADS_PATH, exist_ok=True)


class RoomView(QWidget):
    send_chat    = Signal(str)
    send_file    = Signal(str)
    leave_room   = Signal()
    admit_user   = Signal(int)
    reject_user  = Signal(int)
    camera_toggle = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.es_host = False
        self.sala_info = {}
        self.usuario = {}
        self._camera_active = False
        self._pending_requests = {}
        self._build_ui()

    def setup(self, sala: dict, usuario: dict, es_host: bool):
        self.sala_info = sala
        self.usuario = usuario
        self.es_host = es_host
        nombre_sala = sala.get("nombre_sala", "Sala")
        codigo = sala.get("codigo_sala", "")
        self.lbl_titulo.setText(f"Reunion: {nombre_sala}")
        self.lbl_codigo.setText(f"Codigo: {codigo}")
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

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("QSplitter::handle { background: #2a2a40; }")
        splitter.addWidget(self._build_camera_panel())
        splitter.addWidget(self._build_chat_panel())
        splitter.setSizes([560, 440])

        root.addWidget(splitter)

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

        lbl_local = QLabel("TU CAMARA")
        lbl_local.setStyleSheet("color:#555; font-size:10px; font-weight:bold;")

        self.lbl_cam_local = QLabel()
        self.lbl_cam_local.setFixedSize(320, 240)
        self.lbl_cam_local.setAlignment(Qt.AlignCenter)
        self.lbl_cam_local.setStyleSheet("background:#0d0d1a; border-radius:8px; color:#444; font-size:12px;")
        self.lbl_cam_local.setText("Camara desactivada")

        lbl_remote = QLabel("PARTICIPANTES")
        lbl_remote.setStyleSheet("color:#555; font-size:10px; font-weight:bold;")

        self.lbl_cam_remote = QLabel()
        self.lbl_cam_remote.setMinimumSize(320, 240)
        self.lbl_cam_remote.setAlignment(Qt.AlignCenter)
        self.lbl_cam_remote.setStyleSheet("background:#0d0d1a; border-radius:8px; color:#444; font-size:12px;")
        self.lbl_cam_remote.setText("Sin participantes con camara activa")

        ctrl = QHBoxLayout()
        self.btn_camera = QPushButton("Iniciar camara")
        self.btn_camera.setObjectName("primary")
        self.btn_camera.setFixedHeight(36)
        self.btn_camera.clicked.connect(self._toggle_camera)
        ctrl.addWidget(self.btn_camera)

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

        layout.addWidget(lbl_local)
        layout.addWidget(self.lbl_cam_local, alignment=Qt.AlignHCenter)
        layout.addWidget(lbl_remote)
        layout.addWidget(self.lbl_cam_remote)
        layout.addLayout(ctrl)
        layout.addWidget(self.frame_requests)
        layout.addStretch()

        self.list_participants = QListWidget()
        self.list_participants.setMaximumHeight(120)
        self.list_participants.setStyleSheet("background:#0d0d1a; border-radius:6px; color:#aaa;")
        layout.addWidget(QLabel("Participantes"))
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

    def _toggle_camera(self):
        self._camera_active = not self._camera_active
        if self._camera_active:
            self.btn_camera.setText("Detener camara")
        else:
            self._reset_camera_ui()
        self.camera_toggle.emit(self._camera_active)

    def _reset_camera_ui(self):
        self._camera_active = False
        self.btn_camera.setText("Iniciar camara")
        self.lbl_cam_local.setPixmap(QPixmap())
        self.lbl_cam_local.setText("Camara desactivada")

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

    def add_participant(self, nombre: str):
        self.list_participants.addItem(f"  {nombre}")

    def remove_participant(self, nombre: str):
        for i in range(self.list_participants.count()):
            if nombre in self.list_participants.item(i).text():
                self.list_participants.takeItem(i)
                break

    def add_file(self, nombre: str, remitente: str):
        self.list_files.addItem(f"  {nombre}  (por {remitente})")
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

    def show_camera_frame(self, frame_b64: str):
        raw = base64.b64decode(frame_b64)
        img = QImage()
        img.loadFromData(QByteArray(raw), "JPG")
        if not img.isNull():
            pixmap = QPixmap.fromImage(img).scaled(
                self.lbl_cam_remote.width(),
                self.lbl_cam_remote.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.lbl_cam_remote.setPixmap(pixmap)

    def show_local_frame(self, frame_data):
        from PySide6.QtGui import QImage, QPixmap
        from PySide6.QtCore import Qt
        import base64

        try:
            # Si la data llega como texto Base64, la decodificamos a bytes
            if isinstance(frame_data, str):
                frame_data = base64.b64decode(frame_data)

            # Cargar imagen mágicamente desde los bytes
            img = QImage()
            img.loadFromData(frame_data)

            if not img.isNull():
                pixmap = QPixmap.fromImage(img).scaled(
                    self.lbl_cam_local.width(),
                    self.lbl_cam_local.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.lbl_cam_local.setPixmap(pixmap)
                
        except Exception as e:
            print(f"DEBUG [UI]: Error al mostrar imagen local: {e}")

    def load_history(self, mensajes: list):
        for m in mensajes:
            self.append_chat(m["nombre"], m["texto"])