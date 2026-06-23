class ConnectionManager:
    def __init__(self):
        self.active_connections = {}  # user_id -> websocket

    async def connect(self, user_id, websocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print("Usuario conectado:", user_id)
        print("Conexiones actuales:", self.active_connections.keys())

    def disconnect(self, user_id):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id, message):
        websocket = self.active_connections.get(user_id)
        print(f"Intentando enviar mensaje a {user_id}: {message}", {websocket})
        if websocket:
            try:
                await websocket.send_json(message)
                print(f"Mensaje enviado a {user_id}: {message}")
            except Exception as e:
                print("Error enviando WS:", e)

manager = ConnectionManager()