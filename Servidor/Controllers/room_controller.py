from Database.manager import db_manager as db
import logging

class RoomController:
    @staticmethod
    def handle_create_room(router, msg):
        if not router.usuario:
            return router.send({"tipo": "ERROR", "mensaje": "No autenticado"})
        sala = db.crear_sala(msg.get("nombre_sala", "Mi Sala"), router.usuario["id_usuario"])
        db.agregar_participante(sala["id_sala"], router.usuario["id_usuario"], "admitido")
        router.id_sala = sala["id_sala"]
        router.es_host = True
        router.server.registrar_en_sala(router.id_sala, router)
        router.send({"tipo": "CREATE_ROOM_RESPONSE", "exito": True, "sala": sala})
        logging.info(f"Sala creada: {sala['codigo_sala']} por {router.usuario['nombre']}")

    @staticmethod
    def handle_join_room(router, msg):
        if not router.usuario:
            return router.send({"tipo": "ERROR", "mensaje": "No autenticado"})
        sala = db.obtener_sala_por_codigo(msg.get("codigo_sala", ""))
        if not sala:
            return router.send({"tipo": "JOIN_ROOM_RESPONSE", "exito": False, "error": "Sala no encontrada"})

        db.agregar_participante(sala["id_sala"], router.usuario["id_usuario"], "pendiente")
        router.id_sala = sala["id_sala"]
        router.es_host = False
        router.server.registrar_en_sala(router.id_sala, router)

        host_handler = router.server.get_host_handler(sala["id_sala"])
        if host_handler:
            host_handler.send({
                "tipo": "USER_WANTS_JOIN",
                "id_usuario": router.usuario["id_usuario"],
                "nombre": router.usuario["nombre"],
                "correo": router.usuario["correo"],
            })

        router.send({"tipo": "JOIN_ROOM_RESPONSE", "exito": True, "estado": "pendiente", "sala": sala})
        logging.info(f"{router.usuario['nombre']} solicita entrar a {sala['codigo_sala']}")

    @staticmethod
    def handle_admit_user(router, msg):
        if not router.es_host or not router.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(router.id_sala, id_target, "admitido")

        target = router.find_handler(id_target)
        if target:
            sala_info = db.obtener_sala_por_codigo(router.get_codigo_sala(router.id_sala))
            target.es_host = False
            mensajes_previos = db.obtener_mensajes_sala(router.id_sala)
            participantes_previos = db.obtener_participantes_admitidos(router.id_sala)
            
            target.send({
                "tipo": "ADMITTED_TO_ROOM",
                "sala": sala_info,
                "mensajes_previos": mensajes_previos,
                "participantes_previos": participantes_previos,
            })

        usuario = db.obtener_usuario_por_id(id_target)
        router.server.broadcast_sala(router.id_sala, {
            "tipo": "USER_JOINED",
            "id_usuario": id_target,
            "nombre": usuario["nombre"] if usuario else "Desconocido",
        })

    @staticmethod
    def handle_reject_user(router, msg):
        if not router.es_host or not router.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(router.id_sala, id_target, "rechazado")
        target = router.find_handler(id_target)
        if target:
            target.send({"tipo": "REJECTED_FROM_ROOM"})
            router.server.desregistrar_de_sala(router.id_sala, target)
            logging.info(f"Usuario {id_target} rechazado de la sala {router.id_sala}")
        else:
            logging.warning(f"[REJECT] No se encontró handler para id_usuario={id_target} en sala={router.id_sala}")

    @staticmethod
    def handle_kick_user(router, msg):
        if not router.es_host or not router.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(router.id_sala, id_target, "expulsado")
        target = router.find_handler(id_target)
        if target:
            target.send({"tipo": "KICKED_FROM_ROOM"})
            router.server.desregistrar_de_sala(router.id_sala, target)
            router.server.broadcast_sala(router.id_sala, {
                "tipo": "USER_LEFT",
                "nombre": target.usuario["nombre"] if target.usuario else "Desconocido"
            })

    @staticmethod
    def handle_wait_user(router, msg):
        if not router.es_host or not router.id_sala:
            return
        id_target = msg.get("id_usuario")
        db.actualizar_estado_participante(router.id_sala, id_target, "pendiente")
        target = router.find_handler(id_target)
        if target:
            target.send({"tipo": "SENT_TO_WAITING_ROOM"})
            router.server.desregistrar_de_sala(router.id_sala, target)
            router.server.broadcast_sala(router.id_sala, {
                "tipo": "USER_LEFT",
                "nombre": target.usuario["nombre"] if target.usuario else "Desconocido"
            })
            router.send({
                "tipo": "USER_WANTS_JOIN",
                "id_usuario": target.usuario["id_usuario"],
                "nombre": target.usuario["nombre"],
                "correo": target.usuario["correo"],
            })

    @staticmethod
    def handle_leave_room(router, msg):
        router.cleanup_sala()
