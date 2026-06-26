"""
main.py - Punto de entrada único del prototipo ZoomClone.

Uso:
    python main.py             → menú visual (recomendado)
    python main.py server       → solo servidor (con ventana de control)
    python main.py client       → solo cliente
    python main.py both         → servidor + cliente en la misma PC
"""

import sys
import os

# 1. Rutas maestras y configuración de entorno
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "Servidor"))
sys.path.append(os.path.join(BASE_DIR, "Cliente"))

# 2. Importaciones de la Interfaz
from Servidor.server_window.server_window import ServerWindow
from Cliente.main_client.main_client import MainClient 

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# ─────────────────────────────────────────────────────────────────────────────
# Selector visual
# ─────────────────────────────────────────────────────────────────────────────
def launch_selector():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("ZoomClone")
    app.setQuitOnLastWindowClosed(False)

    selector = QWidget()
    selector.setWindowTitle("ZoomClone – Inicio")
    selector.setFixedSize(440, 360)
    selector.setStyleSheet("""
        QWidget  { background-color: #12121f; color: #e0e0e0; font-family: Arial; }
        QLabel   { color: #e0e0e0; font-family: Arial; }
        QPushButton {
            background: #2D8CFF; color: white; border-radius: 8px;
            font-size: 14px; font-weight: bold; padding: 10px 20px;
        }
        QPushButton:hover { background: #1a7ae0; }
        QPushButton#server_btn { background: #6f42c1; }
        QPushButton#server_btn:hover { background: #5a32a3; }
        QPushButton#both_btn   { background: #28a745; }
        QPushButton#both_btn:hover { background: #218838; }
    """)

    lay = QVBoxLayout(selector)
    lay.setSpacing(20)
    lay.setContentsMargins(40, 30, 40, 30)

    title = QLabel("🎥 ZoomClone")
    title.setFont(QFont("Arial", 24, QFont.Bold))
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("color: #2D8CFF;")
    lay.addWidget(title)

    sub = QLabel("Elige el modo de inicio:")
    sub.setAlignment(Qt.AlignCenter)
    sub.setStyleSheet("color: #888; font-size: 13px;")
    lay.addWidget(sub)

    row = QHBoxLayout()
    btn_s = QPushButton("🖥  Servidor"); btn_s.setObjectName("server_btn")
    btn_c = QPushButton("💻  Cliente")
    btn_b = QPushButton("🚀  Ambos");   btn_b.setObjectName("both_btn")
    for b in (btn_s, btn_c, btn_b):
        b.setFixedHeight(48)
        row.addWidget(b)
    lay.addLayout(row)

    hint = QLabel(
        "Servidor → PC que centraliza la llamada\n"
        "Cliente  → conectarse a un servidor existente\n"
        "Ambos    → ideal para pruebas en una sola PC"
    )
    hint.setStyleSheet("color: #555; font-size: 11px;")
    hint.setAlignment(Qt.AlignCenter)
    lay.addWidget(hint)

    def open_server():
        selector.hide()
        win = ServerWindow()
        app._main_win = win
        win.show()

    def open_client():
        selector.hide()
        win = MainClient(host="127.0.0.1", port=9090)
        app._main_win = win
        win.show()

    def open_both():
        selector.hide()
        srv_win = ServerWindow()
        app._srv_win = srv_win
        srv_win.show()

        def _open_client_now():
            client_win = MainClient(host="127.0.0.1", port=9090)
            app._main_win = client_win
            client_win.show()

        QTimer.singleShot(800, _open_client_now)

    btn_s.clicked.connect(open_server)
    btn_c.clicked.connect(open_client)
    btn_b.clicked.connect(open_both)

    selector.show()
    sys.exit(app.exec())


# ─────────────────────────────────────────────────────────────────────────────
# Modos directos por línea de comandos
# ─────────────────────────────────────────────────────────────────────────────
def run_server_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ServerWindow()
    win.show()
    sys.exit(app.exec())

def run_client_gui(host="127.0.0.1"):
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainClient(host=host, port=9090)
    win.show()
    sys.exit(app.exec())

def run_both_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    srv_win = ServerWindow()
    app._srv_win = srv_win
    srv_win.show()

    def _open_client():
        win = MainClient(host="127.0.0.1", port=9090)
        app._main_win = win
        win.show()

    QTimer.singleShot(800, _open_client)
    sys.exit(app.exec())

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        launch_selector()
    elif args[0] == "server":
        run_server_gui()
    elif args[0] == "client":
        host = args[1] if len(args) > 1 else "127.0.0.1"
        run_client_gui(host=host)
    elif args[0] == "both":
        run_both_gui()
    else:
        print(__doc__)
        sys.exit(1)