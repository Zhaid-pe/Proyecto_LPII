import sys
import os
from PySide6.QtWidgets import QApplication

# Aseguramos que el directorio actual (Servidor) esté en el path para las importaciones
_ROOT = os.path.dirname(__file__)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from UI.server_window import ServerWindow

def main():
    app = QApplication(sys.argv)
    
    # La ventana del servidor inicia la base de datos y arranca el SocketServer en su propio hilo
    window = ServerWindow(host="0.0.0.0", port=9090)
    window.win.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
