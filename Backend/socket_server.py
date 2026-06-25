"""
socket_server.py – Servidor TCP multihilo adaptado para multiplexación de canales.
Escucha conexiones y delega cada cliente a client_handler.
"""

import socket
import threading
import logging

logging.basicConfig(level=logging.INFO, format="[SERVER] %(asctime)s - %(message)s")

HOST = "0.0.0.0"
PORT = 9090


class SocketServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # Estructura compartida: {id_sala: [ClientHandler, ...]}
        self.salas_activas: dict[int, list] = {}
        self.lock = threading.Lock()

    # ── Ciclo principal ────────────────────────────────────────────────────────

    def start(self):
        from Backend.client_handler import ClientHandler  # import tardío para evitar circular

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(50)
        self.running = True
        logging.info(f"Servidor escuchando en {self.host}:{self.port} con soporte de canales multiplexados")

        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logging.info(f"Nueva conexión desde {addr}")
                handler = ClientHandler(client_socket, addr, self)
                t = threading.Thread(target=handler.run, daemon=True)
                t.start()
            except OSError:
                break

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logging.info("Servidor detenido.")

    # ── Gestión de salas activas ───────────────────────────────────────────────

    def registrar_en_sala(self, id_sala: int, handler):
        with self.lock:
            if id_sala not in self.salas_activas:
                self.salas_activas[id_sala] = []
            if handler not in self.salas_activas[id_sala]:
                self.salas_activas[id_sala].append(handler)

    def desregistrar_de_sala(self, id_sala: int, handler):
        with self.lock:
            if id_sala in self.salas_activas:
                self.salas_activas[id_sala] = [
                    h for h in self.salas_activas[id_sala] if h is not handler
                ]

    def broadcast_sala(self, id_sala: int, mensaje: dict, excluir=None):
        """
        Envía un mensaje JSON a todos los clientes admitidos de la sala.
        Hereda automáticamente el canal estructurado 'CMD' definido en ClientHandler.
        """
        with self.lock:
            handlers = list(self.salas_activas.get(id_sala, []))
        for h in handlers:
            if h is not excluir:
                h.send(mensaje)

    def get_host_handler(self, id_sala: int):
        """Devuelve el ClientHandler del host de la sala, o None."""
        with self.lock:
            for h in self.salas_activas.get(id_sala, []):
                if h.es_host:
                    return h
        return None