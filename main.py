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
import threading
import socket

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# Utilidad: obtener IPs locales de la máquina
# ─────────────────────────────────────────────────────────────────────────────

def get_local_ips() -> list[str]:
    """
    Devuelve una lista de IPs locales de la máquina (excluye 127.x.x.x).
    Siempre incluye 127.0.0.1 al final como fallback.
    """
    ips = []
    try:
        # Método principal: conectar a un host externo para descubrir la IP saliente
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
    except OSError:
        pass

    # Método secundario: getaddrinfo para capturar todas las interfaces
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass

    ips.append("127.0.0.1")
    return ips


# ─────────────────────────────────────────────────────────────────────────────
# Ventana de control del servidor
# ─────────────────────────────────────────────────────────────────────────────

class ServerWindow:
    def __init__(self, host="0.0.0.0", port=9090):
        from PySide6.QtWidgets import (
            QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QPushButton, QTextEdit, QFrame, QApplication
        )
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QFont

        self._server = None
        self._log_queue = __import__("queue").Queue()
        self._port = port

        import logging
        class QueueHandler(logging.Handler):
            def __init__(self, q):
                super().__init__()
                self.q = q
            def emit(self, record):
                self.q.put(self.format(record))
        logging.getLogger().addHandler(QueueHandler(self._log_queue))

        self.win = QMainWindow()
        self.win.setWindowTitle("ZoomClone – Servidor")
        self.win.setFixedSize(560, 500)
        self.win.setStyleSheet(
            "QMainWindow, QWidget { background:#12121f; color:#e0e0e0; font-family:Arial; }"
        )

        central = QWidget()
        self.win.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        # ── Título ──
        title = QLabel("🖥  Panel del Servidor")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color:#6f42c1;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        # ── Estado ──
        self.lbl_estado = QLabel("⏳  Iniciando servidor…")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setStyleSheet("font-size:13px; color:#aaa;")
        lay.addWidget(self.lbl_estado)

        # ── Info host/puerto ──
        info_frame = QFrame()
        info_frame.setStyleSheet(
            "background:#1a1a2e; border-radius:8px; padding:4px;"
        )
        info_frame_lay = QHBoxLayout(info_frame)
        lbl_host = QLabel(f"Escuchando en: {host}   Puerto: {port}")
        lbl_host.setStyleSheet("color:#888; font-size:12px;")
        lbl_host.setAlignment(Qt.AlignCenter)
        info_frame_lay.addWidget(lbl_host)
        lay.addWidget(info_frame)

        # ── IPs locales para compartir ──
        ips_frame = QFrame()
        ips_frame.setStyleSheet(
            "background:#0d1a2e; border:1px solid #1a3a5c; border-radius:8px; padding:6px;"
        )
        ips_lay = QVBoxLayout(ips_frame)
        ips_lay.setSpacing(6)

        lbl_ip_title = QLabel("📡  IPs que pueden usar los clientes para conectarse:")
        lbl_ip_title.setStyleSheet("color:#2D8CFF; font-size:12px; font-weight:bold;")
        lbl_ip_title.setAlignment(Qt.AlignCenter)
        ips_lay.addWidget(lbl_ip_title)

        local_ips = get_local_ips()
        for ip in local_ips:
            row = QHBoxLayout()
            icon = "🏠" if ip == "127.0.0.1" else "🌐"
            note = "  (solo esta PC)" if ip == "127.0.0.1" else "  (red local — comparte esta)"
            lbl_ip = QLabel(f"{icon}  {ip}{note}")
            lbl_ip.setStyleSheet(
                "color:#e0e0e0; font-size:13px; font-family:Consolas,monospace;"
                if ip != "127.0.0.1"
                else "color:#666; font-size:12px; font-family:Consolas,monospace;"
            )
            lbl_ip.setAlignment(Qt.AlignCenter)

            btn_copy = QPushButton("Copiar")
            btn_copy.setFixedSize(60, 24)
            btn_copy.setStyleSheet("""
                QPushButton {
                    background:#1e3a5c; color:#88c0d0; border-radius:4px;
                    font-size:11px; border:1px solid #2a5a8c;
                }
                QPushButton:hover { background:#2D8CFF; color:white; border-color:#2D8CFF; }
            """)
            _ip = ip  # captura para el lambda
            btn_copy.clicked.connect(
                lambda checked=False, i=_ip: QApplication.clipboard().setText(i)
            )

            row.addWidget(lbl_ip)
            row.addWidget(btn_copy)
            ips_lay.addLayout(row)

        lay.addWidget(ips_frame)

        # ── Log ──
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "background:#0d0d1a; border:1px solid #2a2a40; border-radius:6px; "
            "color:#88c0d0; font-family:Consolas,monospace; font-size:12px;"
        )
        lay.addWidget(self.log_area)

        # ── Botón detener ──
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

        self._timer = QTimer()
        self._timer.timeout.connect(self._flush_log)
        self._timer.start(200)

        self._thread = threading.Thread(
            target=self._run_server, args=(host, port), daemon=True
        )
        self._thread.start()

    def _run_server(self, host, port):
        from Backend import db_manager
        from Backend.socket_server import SocketServer
        db_manager.init_db()
        self._server = SocketServer(host, port)
        self._log_queue.put("__READY__")
        self._server.start()

    def _flush_log(self):
        while not self._log_queue.empty():
            line = self._log_queue.get_nowait()
            if line == "__READY__":
                self.lbl_estado.setText("✅  Servidor en línea — esperando conexiones")
                self.lbl_estado.setStyleSheet(
                    "font-size:13px; color:#28a745; font-weight:bold;"
                )
                self.btn_stop.setEnabled(True)
                self._append_log("Servidor iniciado correctamente.")
            else:
                self._append_log(line)

    def _append_log(self, text):
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
# Selector visual
# ─────────────────────────────────────────────────────────────────────────────

def launch_selector():
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton
    )
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont

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
        from Frontend.main_client import MainClient
        win = MainClient(host="127.0.0.1", port=9090)
        app._main_win = win
        win.show()

    def open_both():
        selector.hide()
        # 1. Creamos y mostramos la ventana del servidor inmediatamente
        srv_win = ServerWindow()
        app._srv_win = srv_win
        srv_win.show()

        # 2. Programamos de forma segura la inicialización del cliente en el hilo principal
        def _open_client_now():
            from Frontend.main_client import MainClient
            client_win = MainClient(host="127.0.0.1", port=9090)
            app._main_win = client_win
            client_win.show()

        # El temporizador se ejecuta nativamente en la cola de Qt de forma asíncrona
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
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ServerWindow()
    win.show()
    sys.exit(app.exec())


def run_client_gui(host="127.0.0.1"):
    from PySide6.QtWidgets import QApplication
    from Frontend.main_client import MainClient
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainClient(host=host, port=9090)
    win.show()
    sys.exit(app.exec())


def run_both_gui():
    from PySide6.QtWidgets import QApplication
    from Frontend.main_client import MainClient
    from PySide6.QtCore import QTimer

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    # 1. Servidor
    srv_win = ServerWindow()
    app._srv_win = srv_win
    srv_win.show()

    # 2. Cliente diferido nativamente sin hilos intermedios rotos
    def _open_client():
        win = MainClient(host="127.0.0.1", port=9090)
        app._main_win = win
        win.show()

    QTimer.singleShot(800, _open_client)

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