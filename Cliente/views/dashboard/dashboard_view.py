"""
dashboard_view.py Pantalla principal tras el login.
Permite crear una sala o unirse a una por código.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class DashboardView(QWidget):
    create_room_requested = Signal(str)   # nombre de sala
    join_room_requested = Signal(str, str)    # ip, código de sala
    logout_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.usuario = {}
        self._build_ui()

    def set_usuario(self, usuario: dict):
        self.usuario = usuario
        self.lbl_bienvenida.setText(f"Hola, {usuario.get('nombre', '')} 👋")

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #12121f; color: #e0e0e0; font-family: Arial; }
            QLineEdit {
                background: #1e1e2e; border: 1px solid #333; border-radius: 6px;
                padding: 8px 12px; color: #e0e0e0; font-size: 13px;
            }
            QLineEdit:focus { border-color: #2D8CFF; }
            QFrame#card {
                background: #1e1e2e; border: 1px solid #2a2a3e;
                border-radius: 12px; padding: 8px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barra superior ──
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet("background:#0d0d1a; border-bottom: 1px solid #222;")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("🎥 ZoomClone")
        logo.setFont(QFont("Arial", 16, QFont.Bold))
        logo.setStyleSheet("color: #2D8CFF;")

        self.lbl_bienvenida = QLabel("Hola 👋")
        self.lbl_bienvenida.setStyleSheet("color: #aaa; font-size: 13px;")

        btn_logout = QPushButton("Cerrar sesión")
        btn_logout.setFixedSize(110, 32)
        btn_logout.setStyleSheet("""
            QPushButton { background: transparent; color: #ff5555;
                          border: 1px solid #ff5555; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background: #ff5555; color: white; }
        """)
        btn_logout.clicked.connect(self.logout_requested.emit)

        top_layout.addWidget(logo)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_bienvenida)
        top_layout.addSpacing(16)
        top_layout.addWidget(btn_logout)
        root.addWidget(topbar)

        # ── Contenido ──
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(60, 50, 60, 50)
        cl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        cl.setSpacing(24)

        header = QLabel("¿Qué deseas hacer hoy?")
        header.setFont(QFont("Arial", 22, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        cl.addWidget(header)
        cl.addSpacing(10)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(24)
        cards_row.addWidget(self._make_create_card())
        cards_row.addWidget(self._make_join_card())
        cl.addLayout(cards_row)

        root.addWidget(content)

    def _make_create_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(280)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        icon = QLabel("🚀")
        icon.setFont(QFont("Arial", 32))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("Nueva reunión")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        desc = QLabel("Crea una sala y comparte el\ncódigo con tus participantes.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #888; font-size: 12px;")

        self.input_nombre_sala = QLineEdit()
        self.input_nombre_sala.setPlaceholderText("Nombre de la reunión")
        self.input_nombre_sala.setFixedHeight(40)

        btn = QPushButton("Crear reunión")
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton { background: #2D8CFF; color: white; border-radius: 8px;
                          font-size: 13px; font-weight: bold; }
            QPushButton:hover { background: #1a7ae0; }
        """)
        btn.clicked.connect(self._on_create)

        for w in (icon, title, desc, self.input_nombre_sala, btn):
            layout.addWidget(w)
        return card

    def _make_join_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(280)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        icon = QLabel("🔗")
        icon.setFont(QFont("Arial", 32))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("Unirse a reunión")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        desc = QLabel("Ingresa la IP del servidor y el\ncódigo de la reunión.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #888; font-size: 12px;")

        self.input_ip = QLineEdit()
        self.input_ip.setPlaceholderText("IP del servidor (ej. 192.168.1.5)")
        self.input_ip.setFixedHeight(40)
        self.input_ip.setText("127.0.0.1")

        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Código de sala (ej. AB12CD)")
        self.input_codigo.setFixedHeight(40)
        self.input_codigo.setMaxLength(6)

        btn = QPushButton("Unirse")
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton { background: #28a745; color: white; border-radius: 8px;
                          font-size: 13px; font-weight: bold; }
            QPushButton:hover { background: #218838; }
        """)
        btn.clicked.connect(self._on_join)

        for w in (icon, title, desc, self.input_ip, self.input_codigo, btn):
            layout.addWidget(w)
        return card

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_create(self):
        nombre = self.input_nombre_sala.text().strip() or "Mi Reunión"
        self.create_room_requested.emit(nombre)

    def _on_join(self):
        ip = self.input_ip.text().strip() or "127.0.0.1"
        codigo = self.input_codigo.text().strip().upper()
        if len(codigo) == 6:
            self.join_room_requested.emit(ip, codigo)