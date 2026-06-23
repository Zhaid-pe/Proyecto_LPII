"""
login_view.py – Pantalla de autenticación (Login / Registro)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class LoginView(QWidget):
    # Señales emitidas al controlador principal
    login_requested = Signal(str, str)       # correo, password
    register_requested = Signal(str, str, str)  # nombre, correo, password

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("ZoomClone – Iniciar sesión")
        self.setMinimumSize(480, 560)

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setContentsMargins(40, 40, 40, 40)

        # Logo / título
        title = QLabel("ZoomClone")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: #2D8CFF;")
        root.addWidget(title)

        subtitle = QLabel("Prototipo de videollamadas")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888; margin-bottom: 20px;")
        root.addWidget(subtitle)

        # Tabs login / registro
        tabs = QHBoxLayout()
        self.btn_tab_login = QPushButton("Iniciar sesión")
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

        # Stacked widget
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_form())
        self.stack.addWidget(self._build_register_form())
        root.addWidget(self.stack)

        # Conectar tabs
        self.btn_tab_login.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_register.clicked.connect(lambda: self._switch_tab(1))

        # Estilo general
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
        self.login_correo.setPlaceholderText("Correo electrónico")
        self.login_correo.setFixedHeight(42)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Contraseña")
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
        layout.addWidget(QLabel("Contraseña"))
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
        self.reg_correo.setPlaceholderText("Correo electrónico")
        self.reg_correo.setFixedHeight(42)

        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Contraseña")
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_password.setFixedHeight(42)

        self.reg_password2 = QLineEdit()
        self.reg_password2.setPlaceholderText("Confirmar contraseña")
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
                          ("Contraseña", self.reg_password), ("Confirmar contraseña", self.reg_password2)]:
            layout.addWidget(QLabel(lbl))
            layout.addWidget(wdg)
        layout.addSpacing(6)
        layout.addWidget(btn)
        layout.addStretch()
        return widget

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_tab_login.setChecked(index == 0)
        self.btn_tab_register.setChecked(index == 1)

    def _on_login(self):
        correo = self.login_correo.text().strip()
        pwd = self.login_password.text()
        if not correo or not pwd:
            QMessageBox.warning(self, "Campos vacíos", "Por favor completa todos los campos.")
            return
        self.login_requested.emit(correo, pwd)

    def _on_register(self):
        nombre = self.reg_nombre.text().strip()
        correo = self.reg_correo.text().strip()
        pwd = self.reg_password.text()
        pwd2 = self.reg_password2.text()
        if not nombre or not correo or not pwd:
            QMessageBox.warning(self, "Campos vacíos", "Por favor completa todos los campos.")
            return
        if pwd != pwd2:
            QMessageBox.warning(self, "Contraseñas distintas", "Las contraseñas no coinciden.")
            return
        self.register_requested.emit(nombre, correo, pwd)

    def show_error(self, mensaje: str):
        QMessageBox.critical(self, "Error", mensaje)
