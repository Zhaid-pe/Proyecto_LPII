from Database.manager import db_manager as db
import logging

class AuthController:
    @staticmethod
    def handle_login(router, msg):
        usuario = db.validar_usuario(msg.get("correo", ""), msg.get("password", ""))
        if usuario:
            router.usuario = usuario
            router.send({"tipo": "LOGIN_RESPONSE", "exito": True, "usuario": usuario})
            logging.info(f"Login exitoso: {usuario['correo']}")
        else:
            router.send({"tipo": "LOGIN_RESPONSE", "exito": False, "error": "Credenciales inválidas"})

    @staticmethod
    def handle_register(router, msg):
        id_u = db.registrar_usuario(msg.get("nombre", ""), msg.get("correo", ""), msg.get("password", ""))
        if id_u:
            usuario = db.obtener_usuario_por_id(id_u)
            router.usuario = usuario
            router.send({"tipo": "REGISTER_RESPONSE", "exito": True, "usuario": usuario})
        else:
            router.send({"tipo": "REGISTER_RESPONSE", "exito": False, "error": "El correo ya está registrado"})
