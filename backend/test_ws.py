import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8080/ws/1234") as ws:
        await ws.send(json.dumps({
            "type": "task_start",
            "data": {
                "task": "Test",
                "start_url": "https://google.com",
                "execution_mode": "live"
            }
        }))
        while True:
            msg = await ws.recv()
            print("Received:", msg)

asyncio.run(test())
