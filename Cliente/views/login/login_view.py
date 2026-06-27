"""
login_view.py - Pantalla de autenticacion (Login / Registro)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class LoginView(QWidget):
    login_requested    = Signal(str, str, str)   # ip, correo, password
    register_requested = Signal(str, str, str, str)  # ip, nombre, correo, password
    back_requested     = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("ZoomClone")
        self.setMinimumSize(480, 620)

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setContentsMargins(40, 20, 40, 40)

        # ── Botón Volver ──
        self.btn_back = QPushButton("⬅ Volver")
        self.btn_back.setStyleSheet("""
            QPushButton { background: transparent; color: #888; font-weight: bold; border: none; font-size: 14px; text-align: left; }
            QPushButton:hover { color: #fff; }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        root.addWidget(self.btn_back, alignment=Qt.AlignLeft)
        root.addStretch()

        title = QLabel("ZoomClone")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: #2D8CFF;")
        root.addWidget(title)

        subtitle = QLabel("Prototipo de videollamadas")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888; margin-bottom: 10px;")
        root.addWidget(subtitle)

        # ── Campo IP del servidor ──────────────────────────────────────────────
        ip_frame = QFrame()
        ip_frame.setStyleSheet(
            "background: #1a1a2e; border: 1px solid #2a2a50; border-radius: 8px; padding: 4px;"
        )
        ip_layout = QHBoxLayout(ip_frame)
        ip_layout.setContentsMargins(10, 6, 10, 6)

        ip_icon = QLabel("IP del servidor:")
        ip_icon.setStyleSheet("color: #888; font-size: 12px; font-weight: bold;")

        self.input_ip = QLineEdit()
        self.input_ip.setPlaceholderText("Ej: 192.168.1.5  (o 127.0.0.1 si eres el host)")
        self.input_ip.setText("127.0.0.1")
        self.input_ip.setFixedHeight(34)
        self.input_ip.setStyleSheet(
            "background: #232336; border: 1px solid #333; border-radius: 6px;"
            "padding: 4px 10px; color: #e0e0e0; font-size: 13px;"
        )

        ip_layout.addWidget(ip_icon)
        ip_layout.addWidget(self.input_ip)
        root.addWidget(ip_frame)
        root.addSpacing(8)

        # ── Tabs login / registro ──────────────────────────────────────────────
        tabs = QHBoxLayout()
        self.btn_tab_login = QPushButton("Iniciar sesion")
        self.btn_tab_login.setCheckable(True)
        self.btn_tab_login.setChecked(True)
        self.btn_tab_register = QPushButton("Registrarse")
        self.btn_tab_register.setCheckable(True)
        for b in (self.btn_tab_login, self.btn_tab_register):
            b.setFixedHeight(36)
            b.setStyleSheet("""
                QPushButton { background: #1e1e2e; color: #aaa; border: 1px solid #333;
                              border-radius: 6px; font-size: 13px; }
                QPushButton:checked { background: #2D8CFF; color: white; border: none; }
            """)
        tabs.addWidget(self.btn_tab_login)
        tabs.addWidget(self.btn_tab_register)
        root.addLayout(tabs)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_form())
        self.stack.addWidget(self._build_register_form())
        root.addWidget(self.stack)
        root.addStretch()

        self.btn_tab_login.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_register.clicked.connect(lambda: self._switch_tab(1))

        self.setStyleSheet("""
            QWidget { background-color: #12121f; color: #e0e0e0; font-family: Arial; }
            QLineEdit {
                background: #1e1e2e; border: 1px solid #333; border-radius: 6px;
                padding: 8px 12px; color: #e0e0e0; font-size: 13px;
            }
            QLineEdit:focus { border-color: #2D8CFF; }
        """)

    def _build_login_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(14)

        self.login_correo = QLineEdit()
        self.login_correo.setPlaceholderText("Correo electronico")
        self.login_correo.setFixedHeight(42)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Contrasena")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setFixedHeight(42)

        btn = QPushButton("Entrar")
        btn.setFixedHeight(44)
        btn.setStyleSheet("""
            QPushButton { background: #2D8CFF; color: white; border-radius: 8px;
                          font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #1a7ae0; }
            QPushButton:pressed { background: #155cb0; }
        """)
        btn.clicked.connect(self._on_login)
        self.login_password.returnPressed.connect(self._on_login)

        layout.addWidget(QLabel("Correo"))
        layout.addWidget(self.login_correo)
        layout.addWidget(QLabel("Contrasena"))
        layout.addWidget(self.login_password)
        layout.addSpacing(6)
        layout.addWidget(btn)
        layout.addStretch()
        return widget

    def _build_register_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(14)

        self.reg_nombre = QLineEdit()
        self.reg_nombre.setPlaceholderText("Nombre completo")
        self.reg_nombre.setFixedHeight(42)

        self.reg_correo = QLineEdit()
        self.reg_correo.setPlaceholderText("Correo electronico")
        self.reg_correo.setFixedHeight(42)

        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Contrasena")
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_password.setFixedHeight(42)

        self.reg_password2 = QLineEdit()
        self.reg_password2.setPlaceholderText("Confirmar contrasena")
        self.reg_password2.setEchoMode(QLineEdit.Password)
        self.reg_password2.setFixedHeight(42)

        btn = QPushButton("Crear cuenta")
        btn.setFixedHeight(44)
        btn.setStyleSheet("""
            QPushButton { background: #2D8CFF; color: white; border-radius: 8px;
                          font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #1a7ae0; }
            QPushButton:pressed { background: #155cb0; }
        """)
        btn.clicked.connect(self._on_register)

        for lbl, wdg in [("Nombre", self.reg_nombre), ("Correo", self.reg_correo),
                          ("Contrasena", self.reg_password), ("Confirmar contrasena", self.reg_password2)]:
            layout.addWidget(QLabel(lbl))
            layout.addWidget(wdg)
        layout.addSpacing(6)
        layout.addWidget(btn)
        layout.addStretch()
        return widget

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_tab_login.setChecked(index == 0)
        self.btn_tab_register.setChecked(index == 1)

    def get_ip(self) -> str:
        return self.input_ip.text().strip() or "127.0.0.1"

    def _on_login(self):
        correo = self.login_correo.text().strip()
        pwd = self.login_password.text()
        if not correo or not pwd:
            QMessageBox.warning(self, "Campos vacios", "Por favor completa todos los campos.")
            return
        self.login_requested.emit(self.get_ip(), correo, pwd)

    def _on_register(self):
        nombre = self.reg_nombre.text().strip()
        correo = self.reg_correo.text().strip()
        pwd = self.reg_password.text()
        pwd2 = self.reg_password2.text()
        if not nombre or not correo or not pwd:
            QMessageBox.warning(self, "Campos vacios", "Por favor completa todos los campos.")
            return
        if pwd != pwd2:
            QMessageBox.warning(self, "Contrasenas distintas", "Las contrasenas no coinciden.")
            return
        self.register_requested.emit(self.get_ip(), nombre, correo, pwd)

    def show_error(self, mensaje: str):
        QMessageBox.critical(self, "Error", mensaje)