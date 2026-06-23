# ZoomClone – Prototipo de Videollamadas

Prototipo de aplicación de videollamadas desarrollado en Python con PySide6,
sockets TCP nativos y SQLite como base de datos.

---

## Tecnologías

| Capa             | Tecnología                   |
| ---------------- | ---------------------------- |
| Interfaz gráfica | PySide6 (Qt 6)               |
| Red              | `socket` (TCP) + `threading` |
| Base de datos    | SQLite3 (módulo nativo)      |
| Cámara web       | OpenCV (`opencv-python`)     |
| Serialización    | JSON + base64 para binarios  |

---

## Instalación

```bash
pip install PySide6
pip install opencv-python   # opcional, para transmisión de cámara
```

---

## Ejecución

### Modo interactivo (menú visual)

```bash
python main.py
```

### Solo servidor

```bash
python main.py server
```

### Solo cliente (servidor en otra máquina)

```bash
python main.py client 192.168.1.100
```

### Servidor + cliente en la misma PC (pruebas)

```bash
python main.py both
```

---

## Protocolo de mensajes (JSON over TCP)

Cada mensaje es una línea JSON terminada en `\n`.

| Tipo                   | Dirección | Descripción                 |
| ---------------------- | --------- | --------------------------- |
| `LOGIN_REQUEST`        | C→S       | Autenticación               |
| `LOGIN_RESPONSE`       | S→C       | Resultado del login         |
| `REGISTER_REQUEST`     | C→S       | Registro de usuario         |
| `REGISTER_RESPONSE`    | S→C       | Resultado del registro      |
| `CREATE_ROOM`          | C→S       | Crear sala                  |
| `CREATE_ROOM_RESPONSE` | S→C       | Sala creada con código      |
| `JOIN_ROOM_REQUEST`    | C→S       | Solicitar ingreso a sala    |
| `JOIN_ROOM_RESPONSE`   | S→C       | Estado (pendiente/admitido) |
| `USER_WANTS_JOIN`      | S→Host    | Notificación de solicitud   |
| `ADMIT_USER`           | C→S       | Host admite a un usuario    |
| `REJECT_USER`          | C→S       | Host rechaza a un usuario   |
| `ADMITTED_TO_ROOM`     | S→C       | Usuario fue admitido        |
| `REJECTED_FROM_ROOM`   | S→C       | Usuario fue rechazado       |
| `CHAT_MESSAGE`         | C↔S       | Mensaje de chat             |
| `FILE_META`            | C→S       | Inicio de envío de archivo  |
| `FILE_CHUNK`           | C→S       | Bloque de datos (base64)    |
| `FILE_END`             | C→S       | Fin del archivo             |
| `FILE_AVAILABLE`       | S→C       | Archivo listo para descarga |
| `CAMERA_FRAME`         | C↔S       | Frame JPEG en base64        |
| `USER_JOINED`          | S→C       | Participante admitido       |
| `USER_LEFT`            | S→C       | Participante salió          |
| `ROOM_CLOSED`          | S→C       | Host cerró la sala          |
| `LEAVE_ROOM`           | C→S       | Cliente abandona sala       |

---

## Estructura del proyecto

```
Prototipo_Zoom/
├── main.py                  ← Punto de entrada único
├── Backend/
│   ├── db_manager.py        ← Capa de datos (SQLite)
│   ├── socket_server.py     ← Servidor TCP multihilo
│   ├── client_handler.py    ← Procesador del protocolo JSON
│   └── files_storage/       ← Archivos recibidos
├── Frontend/
│   ├── main_client.py       ← Controlador principal (Qt)
│   ├── socket_client.py     ← Conexión TCP + Queue
│   ├── downloads/           ← Archivos descargados
│   └── views/
│       ├── login_view.py    ← Pantalla de login / registro
│       ├── dashboard_view.py← Crear / unirse a sala
│       ├── waiting_view.py  ← Sala de espera
│       └── room_view.py     ← Reunión (chat, archivos, cámara)
├── Database/
│   ├── schema.sql           ← Definición de tablas
│   └── zoom_clone.db        ← BD SQLite (se genera al iniciar)
└── Docs/
    └── README.md
```

---

## Seguridad

- Las contraseñas se almacenan como hash SHA-256; nunca en texto plano.
- El cliente nunca accede directamente a la base de datos.
- Toda comunicación pasa por el servidor.
