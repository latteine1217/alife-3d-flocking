"""
WebSocket Server for Flocking Simulation
提供即時雙向通訊：
- Backend → Frontend: 二進制模擬狀態 (30-60 FPS)
- Frontend → Backend: JSON 控制命令 (start/pause/reset/update_params)
"""

import asyncio
import json
import websockets
from websockets.server import WebSocketServerProtocol

from simulation_manager import SimulationManager
from serializer import BinarySerializer


class FlockingServer:
    """WebSocket 伺服器"""

    def __init__(self, host: str = "localhost", port: int = 8765, initial_config: dict | None = None):
        self.host = host
        self.port = port
        self.manager = SimulationManager(initial_config=initial_config)
        self.running = False

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """處理客戶端連線"""
        print(f"✅ Client connected: {websocket.remote_address}")

        try:
            # 監聽控制訊息
            async def listen_commands():
                async for message in websocket:
                    await self.handle_command(websocket, message)

            # 推送模擬狀態
            async def push_state():
                while True:  # 始終循環
                    if self.manager.system:
                        # 只有在 running 時才執行模擬步驟
                        if self.running:
                            self.manager.step()

                        # 無論是否 running，都傳送當前狀態
                        # 這樣前端連接後就能看到初始狀態
                        data = BinarySerializer.serialize_state(self.manager.system)
                        await websocket.send(data)

                    await asyncio.sleep(0.033)  # ~30 FPS

            # 同時執行兩個任務
            await asyncio.gather(listen_commands(), push_state())

        except websockets.exceptions.ConnectionClosed:
            print(f"❌ Client disconnected: {websocket.remote_address}")
        except Exception as e:
            print(f"⚠️ Error: {e}")

    async def handle_command(self, websocket: WebSocketServerProtocol, message):
        """處理控制命令"""
        try:
            cmd = json.loads(message)
            cmd_type = cmd.get("type")

            if cmd_type == "update_params":
                params = cmd.get("payload")
                print(f"📝 Received update_params: {params}")
                self.manager.update_params(params)
                # 參數更新後自動重新啟動模擬（如果之前正在運行）
                was_running = self.running
                if was_running:
                    print("🔄 Restarting simulation with new parameters...")
                await websocket.send(
                    json.dumps(
                        {
                            "type": "info",
                            "message": "Parameters updated and system reinitialized",
                        }
                    )
                )

            elif cmd_type == "start":
                self.running = True
                await websocket.send(
                    json.dumps({"type": "info", "message": "Simulation started"})
                )

            elif cmd_type == "pause":
                self.running = False
                await websocket.send(
                    json.dumps({"type": "info", "message": "Simulation paused"})
                )

            elif cmd_type == "reset":
                self.manager.reset()
                await websocket.send(
                    json.dumps({"type": "info", "message": "Simulation reset"})
                )

        except json.JSONDecodeError:
            await websocket.send(
                json.dumps({"type": "error", "message": "Invalid JSON"})
            )
        except Exception as e:
            await websocket.send(json.dumps({"type": "error", "message": str(e)}))

    async def start(self):
        """啟動伺服器"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"🚀 Server started at ws://{self.host}:{self.port}")
            print(f"📡 Waiting for connections...")
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    import argparse
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

    from config import load_config, list_configs

    parser = argparse.ArgumentParser(description="ALife WebSocket Server")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help=f"實驗設定檔名稱（不含 .yaml）。可用: {list_configs()}",
    )
    args = parser.parse_args()

    initial_config = None
    if args.config:
        initial_config = load_config(args.config)
        print(f"[Server] 載入設定檔: {args.config}")

    server = FlockingServer(initial_config=initial_config)
    asyncio.run(server.start())
