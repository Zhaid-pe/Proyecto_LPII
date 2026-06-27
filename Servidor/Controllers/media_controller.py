class MediaController:
    @staticmethod
    def handle_raw_video(router, frame_bytes):
        if not router.usuario or not router.id_sala:
            return
        
        user_name_bytes = router.usuario["nombre"][:15].encode("utf-8").ljust(15, b"\0")
        paquete_transmision = user_name_bytes + frame_bytes

        with router.server.lock:
            for handler in router.server.salas_activas.get(router.id_sala, []):
                if handler != router:
                    handler.send_raw_packet("VID", paquete_transmision)

    @staticmethod
    def handle_raw_audio(router, audio_bytes):
        if not router.usuario or not router.id_sala:
            return
        
        user_name_bytes = router.usuario["nombre"][:15].encode("utf-8").ljust(15, b"\0")
        paquete_transmision = user_name_bytes + audio_bytes

        with router.server.lock:
            for handler in router.server.salas_activas.get(router.id_sala, []):
                if handler != router:
                    handler.send_raw_packet("AUD", paquete_transmision)

    @staticmethod
    def handle_camera_off(router, msg):
        if hasattr(router, 'id_sala') and router.id_sala:
            router.server.broadcast_sala(router.id_sala, msg, excluir=router)
