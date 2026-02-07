"""
WebSocket Server 測試腳本
測試 server 是否能正常啟動與接收連線
"""

import asyncio
import websockets
import json


async def test_client():
    """測試客戶端"""
    uri = "ws://localhost:8765"

    print("=== WebSocket Client Test ===\n")
    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!\n")

            # 1. 建立系統
            print("1. Sending update_params command...")
            params = {
                "type": "update_params",
                "payload": {
                    "systemType": "Heterogeneous",
                    "N": 50,
                    "Ca": 1.5,
                    "Cr": 2.0,
                    "la": 2.5,
                    "lr": 0.5,
                    "rc": 15.0,
                    "alpha": 2.0,
                    "v0": 1.0,
                    "beta": 1.0,
                    "eta": 0.0,
                    "boxSize": 50.0,
                    "boundaryMode": "pbc",
                    "agentConfig": {
                        "explorerRatio": 0.3,
                        "followerRatio": 0.5,
                        "enableFov": True,
                        "fovAngle": 120.0,
                    },
                },
            }
            await websocket.send(json.dumps(params))

            response = await websocket.recv()
            print(f"   Response: {response}\n")

            # 2. 啟動模擬
            print("2. Sending start command...")
            await websocket.send(json.dumps({"type": "start"}))

            response = await websocket.recv()
            print(f"   Response: {response}\n")

            # 3. 接收幾幀資料
            print("3. Receiving simulation data (10 frames)...")
            for i in range(10):
                data = await websocket.recv()

                if isinstance(data, bytes):
                    # 解析 header
                    import struct

                    N = struct.unpack("I", data[0:4])[0]
                    step = struct.unpack("I", data[4:8])[0]
                    print(
                        f"   Frame {i + 1}: N={N}, step={step}, size={len(data)} bytes"
                    )
                else:
                    print(f"   Unexpected JSON: {data}")

            print("\n4. Sending pause command...")
            await websocket.send(json.dumps({"type": "pause"}))

            response = await websocket.recv()
            print(f"   Response: {response}\n")

            print("✅ Test completed successfully!")

    except ConnectionRefusedError:
        print("❌ Connection refused. Make sure the server is running:")
        print("   uv run python server.py")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_client())
