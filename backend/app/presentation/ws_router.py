from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)

    async def broadcast(self, room_id: str, message: dict):
        for connection in self.active_connections.get(room_id, []):
            try:
                await connection.send_json(message)
            except:
                pass

ws_manager = ConnectionManager()

@router.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await ws_manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast(room_id, {"sender": "user", "message": data, "timestamp": str(datetime.utcnow())})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room_id)
        await ws_manager.broadcast(room_id, {"sender": "system", "message": "A user disconnected"})