# Backend WebSocket Server

Python WebSocket 伺服器，將 Taichi 模擬狀態即時傳送至前端。

## 架構

```
Backend (Python)
├── server.py              # WebSocket 伺服器（asyncio）
├── simulation_manager.py  # 包裝 Taichi solver
├── serializer.py          # 二進制序列化器
└── test_client.py         # 測試客戶端
```

## 依賴安裝

```bash
cd backend
uv pip install -r requirements.txt
```

## 測試

### 1. 測試 SimulationManager

```bash
uv run python simulation_manager.py
```

預期輸出：
```
✅ Created Heterogeneous system with N=100
   System N: 100
   Mean speed: 0.xxx
   Polarization: 0.xxx
```

### 2. 測試序列化效能

```bash
uv run python serializer.py
```

預期輸出：
```
Frame size: 3384 bytes (3.30 KB)
Speed: 300+ FPS
Latency: <4 ms/frame
```

### 3. 測試 WebSocket Server

**終端機 1** - 啟動伺服器：
```bash
uv run python server.py
```

**終端機 2** - 執行測試客戶端：
```bash
uv run python test_client.py
```

預期輸出：
```
✅ Connected successfully!
   Response: {"type": "info", "message": "Parameters updated"}
   Frame 1: N=50, step=1, size=1734 bytes
   Frame 2: N=50, step=2, size=1734 bytes
   ...
✅ Test completed successfully!
```

## 資料格式

### Binary Frame (Backend → Frontend)

```
Header (20 bytes):
  - N: uint32 (4 bytes)
  - step: uint32 (4 bytes)
  - has_resources: uint8 (1 byte)
  - has_obstacles: uint8 (1 byte)
  - reserved: 10 bytes

Agent Data (N * 33 bytes):
  - positions: float32[N][3]
  - velocities: float32[N][3]
  - types: uint8[N]
  - energies: float32[N]
  - targets: int32[N]

Statistics (64 bytes):
  - mean_speed, std_speed, Rg, polarization, etc.

Resources (optional):
  - n_resources: uint32
  - [positions, amounts, radii] * n_resources
```

**效能**：
- N=100: ~3.4 KB/frame
- N=500: ~16.5 KB/frame
- @ 30 FPS: ~100-500 KB/s

### Control Commands (Frontend → Backend, JSON)

```json
// 更新參數
{
  "type": "update_params",
  "payload": {
    "systemType": "Heterogeneous",
    "N": 100,
    "Ca": 1.5,
    ...
  }
}

// 啟動模擬
{ "type": "start" }

// 暫停模擬
{ "type": "pause" }

// 重置模擬
{ "type": "reset" }
```

## API

### SimulationManager

```python
manager = SimulationManager()

# 建立系統
manager.create_system(params_dict)

# 執行一幀
manager.step()

# 重置
manager.reset()

# 更新參數（重建系統）
manager.update_params(params_dict)
```

### BinarySerializer

```python
# 序列化系統狀態
data = BinarySerializer.serialize_state(system)

# 計算資料大小
size = BinarySerializer.get_frame_size(N=100, n_resources=5)
```

## 已知問題

1. **Taichi 重複初始化警告**：每次 `create_system()` 會重新初始化 Taichi，可忽略警告
2. **資源數量限制**：最多 32 個資源（`max_resources` 參數）
3. **目前不支援障礙物序列化**

## 效能指標

| Metric | Value |
|--------|-------|
| 序列化速度 | 300+ FPS |
| 延遲 | < 4 ms/frame |
| 資料大小 (N=100) | 3.4 KB |
| 頻寬 (30 FPS) | ~100 KB/s |

## 下一步

✅ Backend 已完成並測試通過
⏳ 下一階段：Frontend (React + TypeScript + WebSocket Client)
