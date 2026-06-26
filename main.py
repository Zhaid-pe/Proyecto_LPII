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

# 2. Importamos el lanzador recién creado
from launcher import launch_selector, run_server_gui, run_client_gui, run_both_gui

# 3. Punto de entrada limpio
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