import json

from fastapi import WebSocket

from app.core.redis import client, STREAM_TRANSACTIONS


class WebSocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def broadcast(self, message: dict):
        for websocket in self.connections:
            await websocket.send_json(message)

    async def listen_redis(self):
        pubsub = client.pubsub()
        await pubsub.subscribe(STREAM_TRANSACTIONS)

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await self.broadcast(data)

manager = WebSocketManager()