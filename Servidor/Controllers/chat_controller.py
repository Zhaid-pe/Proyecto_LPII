from Database.manager import db_manager as db

class ChatController:
    @staticmethod
    def handle_chat_message(router, msg):
        if not router.usuario or not router.id_sala:
            return
        texto = msg.get("texto", "").strip()
        if not texto:
            return
        db.guardar_mensaje(router.id_sala, router.usuario["id_usuario"], texto)
        router.server.broadcast_sala(router.id_sala, {
            "tipo": "CHAT_MESSAGE",
            "id_usuario": router.usuario["id_usuario"],
            "nombre": router.usuario["nombre"],
            "texto": texto,
        })
