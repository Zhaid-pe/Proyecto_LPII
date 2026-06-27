import os
import base64
import logging
from Database.manager import db_manager as db

STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "files_storage")

class FileController:
    @staticmethod
    def handle_file_meta(router, msg):
        router._file_meta = msg
        router._file_chunks = []
        logging.info(f"Recibiendo archivo: {msg.get('nombre_archivo')}")

    @staticmethod
    def handle_file_chunk(router, msg):
        chunk_b64 = msg.get("data", "")
        router._file_chunks.append(base64.b64decode(chunk_b64))

    @staticmethod
    def handle_file_end(router, msg):
        if not router._file_meta or not router.usuario or not router.id_sala:
            return
        nombre = router._file_meta.get("nombre_archivo", "archivo.bin")
        ruta = os.path.join(STORAGE_PATH, f"{router.id_sala}_{nombre}")
        data_completa = b"".join(router._file_chunks)
        
        os.makedirs(STORAGE_PATH, exist_ok=True)
        with open(ruta, "wb") as f:
            f.write(data_completa)

        id_archivo = db.registrar_archivo(
            router.id_sala, router.usuario["id_usuario"],
            nombre, ruta, len(data_completa)
        )
        logging.info(f"Archivo guardado: {nombre} ({len(data_completa)} bytes)")

        router.server.broadcast_sala(router.id_sala, {
            "tipo": "FILE_AVAILABLE",
            "id_archivo": id_archivo,
            "nombre_archivo": nombre,
            "tamanio_bytes": len(data_completa),
            "remitente": router.usuario["nombre"],
        })
        router._file_meta = None
        router._file_chunks = []

    @staticmethod
    def handle_download_request(router, msg):
        nombre_archivo = msg.get("nombre_archivo")
        if not nombre_archivo or not router.id_sala: 
            return
            
        ruta = os.path.join(STORAGE_PATH, f"{router.id_sala}_{nombre_archivo}")
        
        if not os.path.exists(ruta):
            router.send({"tipo": "ERROR", "mensaje": f"El archivo {nombre_archivo} no existe en el servidor."})
            return
            
        try:
            with open(ruta, "rb") as f:
                while True:
                    chunk = f.read(32768)
                    if not chunk: 
                        break
                    
                    router.send({
                        "tipo": "DOWNLOAD_CHUNK", 
                        "nombre_archivo": nombre_archivo, 
                        "data": base64.b64encode(chunk).decode("ascii")
                    })
                    
            router.send({"tipo": "DOWNLOAD_END", "nombre_archivo": nombre_archivo})
            logging.info(f"Archivo enviado a cliente: {nombre_archivo}")
            
        except Exception as e:
            router.send({"tipo": "ERROR", "mensaje": f"Error al enviar archivo: {e}"})
