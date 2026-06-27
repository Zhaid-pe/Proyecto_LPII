import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# Importaciones de la Interfaz
from Servidor.UI.server_window import ServerWindow
from Cliente.main import AppMediator

# ─────────────────────────────────────────────────────────────────────────────
# Selector visual
# ─────────────────────────────────────────────────────────────────────────────
def launch_selector():
    app = QApplication.instance() or QApplication(sys.argv)
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

    def go_back(win):
        if hasattr(win, 'win'):
            win.win.hide()
            win.win.deleteLater()
        else:
            win.hide()
            win.deleteLater()
        selector.show()

    def open_server():
        selector.hide()
        win = ServerWindow(on_back=lambda: go_back(win))
        app._main_win = win
        win.show()

    def open_client():
        selector.hide()
        win = AppMediator()
        win._current_host = "127.0.0.1"
        win._port = 9090
        win.on_back = lambda: go_back(win.window)
        app._main_win = win
        win.window.show()
        win.message_router.start()

    def open_both():
        selector.hide()

        def _back_both():
            if hasattr(app, '_srv_win') and app._srv_win:
                app._srv_win.on_back = None
                if hasattr(app._srv_win, 'win'):
                    app._srv_win.win.hide()
                    app._srv_win.win.deleteLater()
                else:
                    app._srv_win.hide()
                    app._srv_win.deleteLater()
                app._srv_win = None
            if hasattr(app, '_main_win') and app._main_win:
                app._main_win.on_back = None
                app._main_win.window.hide()
                app._main_win.window.deleteLater()
                app._main_win = None
            selector.show()

        srv_win = ServerWindow(on_back=_back_both)
        app._srv_win = srv_win
        srv_win.show()

        def _open_client_now():
            client_win = AppMediator()
            client_win._current_host = "127.0.0.1"
            client_win._port = 9090
            client_win.on_back = _back_both
            app._main_win = client_win
            client_win.window.show()
            client_win.message_router.start()

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
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ServerWindow()
    win.show()
    sys.exit(app.exec())

def run_client_gui(host="127.0.0.1"):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    win = AppMediator()
    win._current_host = host
    win.window.show()
    win.message_router.start()
    sys.exit(app.exec())

def run_both_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    srv_win = ServerWindow()
    app._srv_win = srv_win
    srv_win.show()

    def _open_client():
        win = AppMediator()
        win._current_host = "127.0.0.1"
        app._main_win = win
        win.window.show()
        win.message_router.start()

    QTimer.singleShot(800, _open_client)
    sys.exit(app.exec())