import sys
import os
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import Signal, QTimer

from .login_view import LoginView
from .dashboard_view import DashboardView
from .waiting_view import WaitingView
from .room_view import RoomView

IDX_LOGIN     = 0
IDX_DASHBOARD = 1
IDX_WAITING   = 2
IDX_ROOM      = 3

class MainWindow(QMainWindow):
    # Senales que el orquestador principal (main.py) puede escuchar
    go_back_requested = Signal()
    logout_requested = Signal()
    leave_room_requested = Signal()
    
    def __init__(self, on_back=None):
        super().__init__()
        self.on_back = on_back
        self.setWindowTitle("ZoomClone")
        self.setMinimumSize(1100, 680)

        # Vistas
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_view     = LoginView()
        self.dashboard_view = DashboardView()
        self.waiting_view   = WaitingView()
        self.room_view      = RoomView()

        self.stack.addWidget(self.login_view)
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.waiting_view)
        self.stack.addWidget(self.room_view)

        self._setup_internal_connections()

    def _setup_internal_connections(self):
        # Conexiones internas para que la vista propague acciones de navegación si es necesario
        self.login_view.back_requested.connect(self._go_back)
        self.dashboard_view.logout_requested.connect(self.logout_requested.emit)
        self.waiting_view.cancel_requested.connect(self.leave_room_requested.emit)
        self.room_view.leave_room.connect(self.leave_room_requested.emit)

    def _go_back(self):
        if self.stack.currentIndex() == IDX_LOGIN:
            self._is_going_back = True
            self.go_back_requested.emit()
            if self.on_back:
                self.on_back()
            self.close()
        else:
            self.logout_requested.emit()

    def go_to(self, index: int):
        self.stack.setCurrentIndex(index)

    def show_error(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)
        
    def show_critical(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event):
        # El cierre real (stop threads, disconnect) será manejado interceptando esta señal o desde main
        event.accept()
        if not getattr(self, '_is_going_back', False):
            os._exit(0)
