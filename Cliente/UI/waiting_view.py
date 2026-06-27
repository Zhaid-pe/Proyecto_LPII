"""
waiting_view.py Sala de espera mientras el host admite al usuario.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QMovie
from PySide6.QtCore import QTimer


class WaitingView(QWidget):
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._start_animation()

    def set_info(self, nombre_sala: str, codigo: str):
        self.lbl_sala.setText(f"<b>{nombre_sala}</b>")
        self.lbl_codigo.setText(f"Código: <span style='color:#2D8CFF;font-weight:bold'>{codigo}</span>")

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("QWidget { background-color: #12121f; color: #e0e0e0; font-family: Arial; }")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(60, 60, 60, 60)

        # Spinner animado (texto)
        self.lbl_spinner = QLabel("⏳")
        self.lbl_spinner.setFont(QFont("Arial", 48))
        self.lbl_spinner.setAlignment(Qt.AlignCenter)

        title = QLabel("Sala de espera")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        self.lbl_sala = QLabel("—")
        self.lbl_sala.setFont(QFont("Arial", 14))
        self.lbl_sala.setAlignment(Qt.AlignCenter)

        self.lbl_codigo = QLabel("")
        self.lbl_codigo.setFont(QFont("Arial", 13))
        self.lbl_codigo.setAlignment(Qt.AlignCenter)
        self.lbl_codigo.setTextFormat(Qt.RichText)

        info = QLabel("Espera mientras el anfitrión te admite a la reunión.")
        info.setStyleSheet("color: #888; font-size: 13px;")
        info.setAlignment(Qt.AlignCenter)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedSize(130, 38)
        btn_cancel.setStyleSheet("""
            QPushButton { background: transparent; color: #ff5555;
                          border: 1px solid #ff5555; border-radius: 6px; }
            QPushButton:hover { background: #ff5555; color: white; }
        """)
        btn_cancel.clicked.connect(self.cancel_requested.emit)

        for w in (self.lbl_spinner, title, self.lbl_sala, self.lbl_codigo, info, btn_cancel):
            layout.addWidget(w)

    def _start_animation(self):
        emojis = ["⏳", "⌛"]
        self._anim_index = 0

        def tick():
            self._anim_index = (self._anim_index + 1) % len(emojis)
            self.lbl_spinner.setText(emojis[self._anim_index])

        self._timer = QTimer(self)
        self._timer.timeout.connect(tick)
        self._timer.start(800)
