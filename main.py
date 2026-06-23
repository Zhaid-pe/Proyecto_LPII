"""
main.py – Punto de entrada único del prototipo ZoomClone.

Uso:
    python main.py              → menú visual (recomendado)
    python main.py server       → solo servidor (con ventana de control)
    python main.py client       → solo cliente
    python main.py both         → servidor + cliente en la misma PC
"""

import sys
import os
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# Ventana de control del servidor
# ─────────────────────────────────────────────────────────────────────────────

class ServerWindow:
    """
    Ventana PySide6 que muestra el estado del servidor y permite detenerlo.
    El servidor corre en un hilo daemon; esta ventana vive en el hilo principal.
    """

    def __init__(self, app, host="0.0.0.0", port=9090):
        from PySide6.QtWidgets import (
            QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QPushButton, QTextEdit, QFrame
        )
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QFont, QTextCursor

        self._server = None
        self._log_queue = __import__("queue").Queue()

        # ── Parchear el logging para capturar mensajes ──────────────────────
        import logging

        class QueueHandler(logging.Handler):
            def __init__(self, q):
                super().__init__()
                self.q = q
            def emit(self, record):
                self.q.put(self.format(record))

        logging.getLogger().addHandler(QueueHandler(self._log_queue))

        # ── Ventana ─────────────────────────────────────────────────────────
        self.win = QMainWindow()
        self.win.setWindowTitle("ZoomClone – Servidor")
        self.win.setFixedSize(520, 420)
        self.win.setStyleSheet("QMainWindow, QWidget { background:#12121f; color:#e0e0e0; font-family:Arial; }")

        central = QWidget()
        self.win.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # Título
        title = QLabel("🖥  Panel del Servidor")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color:#6f42c1;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        # Estado
        self.lbl_estado = QLabel("⏳  Iniciando servidor…")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setStyleSheet("font-size:13px; color:#aaa;")
        lay.addWidget(self.lbl_estado)

        # Info de conexión
        info_frame = QFrame()
        info_frame.setStyleSheet("background:#1a1a2e; border-radius:8px; padding:4px;")
        info_lay = QHBoxLayout(info_frame)
        self.lbl_host = QLabel(f"Host: {host}   Puerto: {port}")
        self.lbl_host.setStyleSheet("color:#888; font-size:12px;")
        self.lbl_host.setAlignment(Qt.AlignCenter)
        info_lay.addWidget(self.lbl_host)
        lay.addWidget(info_frame)

        # Log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "background:#0d0d1a; border:1px solid #2a2a40; border-radius:6px; "
            "color:#88c0d0; font-family:Consolas,monospace; font-size:12px;"
        )
        lay.addWidget(self.log_area)

        # Botón detener
        self.btn_stop = QPushButton("⏹  Detener servidor")
        self.btn_stop.setFixedHeight(42)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background:#dc3545; color:white; border-radius:8px;
                          font-size:14px; font-weight:bold; }
            QPushButton:hover { background:#b02a37; }
            QPushButton:disabled { background:#3a1a1f; color:#555; }
        """)
        self.btn_stop.clicked.connect(self._stop)
        lay.addWidget(self.btn_stop)

        # Timer para vaciar el log_queue → QTextEdit
        self._timer = QTimer()
        self._timer.timeout.connect(self._flush_log)
        self._timer.start(200)

        # Arrancar el servidor en hilo daemon
        self._thread = threading.Thread(target=self._run_server, args=(host, port), daemon=True)
        self._thread.start()

    def _run_server(self, host, port):
        from Backend import db_manager
        from Backend.socket_server import SocketServer

        db_manager.init_db()
        self._server = SocketServer(host, port)

        # Señal a la GUI (thread-safe mediante la cola)
        self._log_queue.put("__READY__")
        self._server.start()   # bloqueante hasta stop()

    def _flush_log(self):
        from PySide6.QtGui import QTextCursor
        changed = False
        while not self._log_queue.empty():
            line = self._log_queue.get_nowait()
            if line == "__READY__":
                self.lbl_estado.setText("✅  Servidor en línea — esperando conexiones")
                self.lbl_estado.setStyleSheet("font-size:13px; color:#28a745; font-weight:bold;")
                self.btn_stop.setEnabled(True)
                self._append_log("Servidor iniciado correctamente.")
            else:
                self._append_log(line)
            changed = True

    def _append_log(self, text: str):
        from PySide6.QtGui import QTextCursor
        self.log_area.append(text)
        self.log_area.moveCursor(QTextCursor.End)

    def _stop(self):
        if self._server:
            self._server.stop()
        self.lbl_estado.setText("🔴  Servidor detenido")
        self.lbl_estado.setStyleSheet("font-size:13px; color:#dc3545;")
        self.btn_stop.setEnabled(False)
        self._append_log("Servidor detenido por el usuario.")

    def show(self):
        self.win.show()


# ─────────────────────────────────────────────────────────────────────────────
# Funciones de arranque
# ─────────────────────────────────────────────────────────────────────────────

def _make_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("ZoomClone")
    return app


def run_server_gui(host="0.0.0.0", port=9090):
    """Servidor con ventana de control (no bloqueante en la GUI)."""
    app = _make_app()
    win = ServerWindow(app, host, port)
    win.show()
    sys.exit(app.exec())


def run_client_gui(host="127.0.0.1", port=9090):
    """Solo cliente."""
    app = _make_app()
    from Frontend.main_client import MainClient
    win = MainClient(host=host, port=port)
    win.show()
    sys.exit(app.exec())


def run_both_gui(host="127.0.0.1", port=9090):
    """Servidor en hilo daemon + cliente en la misma QApplication."""
    from Backend import db_manager
    from Backend.socket_server import SocketServer

    db_manager.init_db()
    _srv = SocketServer("0.0.0.0", port)
    t = threading.Thread(target=_srv.start, daemon=True, name="ZoomServer")
    t.start()
    time.sleep(0.6)   # esperar a que el socket esté listo

    app = _make_app()
    from Frontend.main_client import MainClient
    win = MainClient(host=host, port=port)
    win.show()
    sys.exit(app.exec())


# ─────────────────────────────────────────────────────────────────────────────
# Selector visual
# ─────────────────────────────────────────────────────────────────────────────

def launch_selector():
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    app = _make_app()

    dialog = QDialog()
    dialog.setWindowTitle("ZoomClone – Inicio")
    dialog.setFixedSize(440, 360)
    dialog.setStyleSheet("""
        QDialog  { background-color: #12121f; }
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

    lay = QVBoxLayout(dialog)
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

    chosen = {"value": None}

    def pick(m):
        chosen["value"] = m
        dialog.accept()

    row = QHBoxLayout()
    btn_s = QPushButton("🖥  Servidor");  btn_s.setObjectName("server_btn")
    btn_c = QPushButton("💻  Cliente")
    btn_b = QPushButton("🚀  Ambos");    btn_b.setObjectName("both_btn")

    btn_s.clicked.connect(lambda: pick("server"))
    btn_c.clicked.connect(lambda: pick("client"))
    btn_b.clicked.connect(lambda: pick("both"))

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

    dialog.exec()

    mode = chosen["value"]
    if not mode:
        sys.exit(0)

    # Toda la lógica posterior reutiliza la misma QApplication
    if mode == "server":
        win = ServerWindow(app, host="0.0.0.0", port=9090)
        win.show()
        sys.exit(app.exec())

    elif mode == "client":
        from Frontend.main_client import MainClient
        win = MainClient(host="127.0.0.1", port=9090)
        win.show()
        sys.exit(app.exec())

    elif mode == "both":
        from Backend import db_manager
        from Backend.socket_server import SocketServer
        db_manager.init_db()
        srv = SocketServer("0.0.0.0", 9090)
        threading.Thread(target=srv.start, daemon=True, name="ZoomServer").start()
        time.sleep(0.6)
        from Frontend.main_client import MainClient
        win = MainClient(host="127.0.0.1", port=9090)
        win.show()
        sys.exit(app.exec())


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────

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
