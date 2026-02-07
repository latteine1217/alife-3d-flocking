# React + TypeScript + WebGPU 整合計畫

**目標**: 將現有 Taichi Solver 與 React + WebGPU 前端整合  
**預計時間**: 3 週  
**開發策略**: 增量式開發，保持現有 Solver 不變

---

## 🏗️ 系統架構設計

### 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Browser)                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  React Application (TypeScript)                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │ Control Panel│  │  Statistics  │  │  3D Canvas      │  │ │
│  │  │ (參數調整)    │  │  (即時統計)   │  │  (WebGPU)       │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │ │
│  │         │                  ↑                   ↑            │ │
│  │         └──────────────────┼───────────────────┘            │ │
│  │                            │                                │ │
│  │  ┌─────────────────────────┴──────────────────────────────┐ │ │
│  │  │  State Manager (Zustand / Jotai)                       │ │ │
│  │  │  - simulationState: SimulationData                     │ │ │
│  │  │  - parameters: SimulationParams                        │ │ │
│  │  │  - connection: WebSocket                               │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  │                            ↓                                │ │
│  │  ┌─────────────────────────┴──────────────────────────────┐ │ │
│  │  │  WebSocket Client (Binary Protocol)                    │ │ │
│  │  │  - 接收: Position, Velocity, Energy, Resources          │ │ │
│  │  │  - 發送: Parameter updates, Control commands           │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────┘
                                │ WebSocket (Binary)
                                │ ws://localhost:8765
┌───────────────────────────────┴───────────────────────────────────┐
│  Backend (Python)                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  WebSocket Server (asyncio + websockets)                   │  │
│  │  - 處理參數更新請求                                          │  │
│  │  - 每幀推送模擬狀態                                          │  │
│  │  - 支援多客戶端（可選）                                       │  │
│  └───────────────────────┬────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Simulation Manager                                         │  │
│  │  - 系統創建與初始化                                          │  │
│  │  - 參數熱更新（重建系統）                                     │  │
│  │  - 模擬循環控制                                              │  │
│  └───────────────────────┬────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Taichi Solver (現有程式碼，無需修改)                        │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ HeterogeneousFlocking3D                              │  │  │
│  │  │  - x: ti.Vector.field (N x 3, 位置)                  │  │  │
│  │  │  - v: ti.Vector.field (N x 3, 速度)                  │  │  │
│  │  │  - agent_types: ti.field (N, agent 類型)             │  │  │
│  │  │  - step(dt): 執行一幀模擬                             │  │  │
│  │  │  - compute_diagnostics(): 計算統計資訊                │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ResourceSystem (覓食系統)                             │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ObstacleSystem (障礙物系統)                           │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 資料流設計

### 1. 模擬狀態資料（Backend → Frontend）

**資料結構**（每幀傳輸）:

```python
# Python (Backend)
class SimulationState:
    """每幀傳輸的資料（二進位格式）"""
    
    # Header (20 bytes)
    N: uint32              # 4 bytes - Agent 數量
    step: uint32           # 4 bytes - 當前步數
    has_resources: uint8   # 1 byte  - 是否有資源
    has_obstacles: uint8   # 1 byte  - 是否有障礙物
    reserved: bytes        # 10 bytes - 保留欄位
    
    # Agent Data (N * 32 bytes)
    positions: float32[N][3]    # N * 12 bytes - 位置 (x, y, z)
    velocities: float32[N][3]   # N * 12 bytes - 速度 (vx, vy, vz)
    types: uint8[N]             # N * 1 byte   - Agent 類型
    energies: float32[N]        # N * 4 bytes  - 能量（異質性系統）
    targets: int32[N]           # N * 4 bytes  - 目標 resource ID (-1 = 無)
    
    # Statistics (64 bytes)
    mean_speed: float32         # 4 bytes
    std_speed: float32          # 4 bytes
    Rg: float32                 # 4 bytes - 回旋半徑
    polarization: float32       # 4 bytes - 極化參數
    n_groups: uint32            # 4 bytes - 群組數量
    reserved_stats: bytes       # 44 bytes
    
    # Resources (optional, if has_resources=1)
    n_resources: uint32                   # 4 bytes
    resource_positions: float32[n_res][3] # n_res * 12 bytes
    resource_amounts: float32[n_res]      # n_res * 4 bytes
    resource_radii: float32[n_res]        # n_res * 4 bytes
    
    # Total size per frame (N=100):
    # Header: 20 bytes
    # Agents: 100 * 33 = 3300 bytes
    # Stats: 64 bytes
    # Resources (2): 2 * 20 = 40 bytes
    # Total: ~3.4 KB per frame
    # @ 30 FPS → ~100 KB/s (可接受)
```

**序列化實作**（Python）:

```python
# backend/serializer.py
import struct
import numpy as np

class BinarySerializer:
    """高效能二進位序列化器"""
    
    @staticmethod
    def serialize_state(system) -> bytes:
        """
        序列化模擬狀態為二進位格式
        
        Args:
            system: HeterogeneousFlocking3D 實例
            
        Returns:
            bytes: 二進位資料
        """
        N = system.N
        
        # 提取資料（從 GPU 到 CPU）
        x_np = system.x.to_numpy()  # (N, 3) float32
        v_np = system.v.to_numpy()  # (N, 3) float32
        types_np = system.agent_types.to_numpy()  # (N,) uint8
        
        # 計算統計（使用現有方法）
        diag = system.compute_diagnostics()
        
        # 異質性資料
        has_energy = hasattr(system, 'get_agent_energies')
        energies_np = system.get_agent_energies() if has_energy else np.zeros(N, dtype=np.float32)
        targets_np = system.get_agent_targets() if hasattr(system, 'get_agent_targets') else np.full(N, -1, dtype=np.int32)
        
        # 資源資料
        has_resources = hasattr(system, 'get_all_resources')
        resources = system.get_all_resources() if has_resources else []
        
        # 群組資訊
        n_groups = len(system.get_all_groups()) if hasattr(system, 'get_all_groups') else 0
        
        # ===== 開始打包 =====
        buffer = bytearray()
        
        # Header (20 bytes)
        buffer.extend(struct.pack('I', N))                    # N
        buffer.extend(struct.pack('I', system.step_count))    # step
        buffer.extend(struct.pack('B', int(has_resources)))   # has_resources
        buffer.extend(struct.pack('B', 0))                    # has_obstacles (未實作)
        buffer.extend(b'\x00' * 10)                           # reserved
        
        # Agent Data (N * 33 bytes)
        buffer.extend(x_np.astype(np.float32).tobytes())         # positions (N * 12)
        buffer.extend(v_np.astype(np.float32).tobytes())         # velocities (N * 12)
        buffer.extend(types_np.astype(np.uint8).tobytes())       # types (N * 1)
        
        # Padding to align (N * 1 → N * 4)
        padding = (4 - (N % 4)) % 4
        buffer.extend(b'\x00' * padding)
        
        buffer.extend(energies_np.astype(np.float32).tobytes())  # energies (N * 4)
        buffer.extend(targets_np.astype(np.int32).tobytes())     # targets (N * 4)
        
        # Statistics (64 bytes)
        buffer.extend(struct.pack('f', diag['mean_speed']))
        buffer.extend(struct.pack('f', diag['std_speed']))
        buffer.extend(struct.pack('f', diag['Rg']))
        buffer.extend(struct.pack('f', diag['polarization']))
        buffer.extend(struct.pack('I', n_groups))
        buffer.extend(b'\x00' * 44)  # reserved
        
        # Resources (optional)
        if has_resources:
            n_res = len(resources)
            buffer.extend(struct.pack('I', n_res))
            
            for res in resources:
                pos = res['position']
                buffer.extend(struct.pack('fff', pos[0], pos[1], pos[2]))
                buffer.extend(struct.pack('f', res['amount']))
                buffer.extend(struct.pack('f', res['radius']))
                buffer.extend(struct.pack('B', int(res['replenish_rate'] > 0)))  # is_renewable
                buffer.extend(b'\x00' * 3)  # padding
        
        return bytes(buffer)
    
    @staticmethod
    def get_frame_size(N: int, n_resources: int = 0) -> int:
        """計算單幀資料大小"""
        header = 20
        agents = N * 33
        stats = 64
        resources = n_resources * 20 if n_resources > 0 else 0
        return header + agents + stats + resources
```

**反序列化實作**（TypeScript）:

```typescript
// frontend/src/lib/deserializer.ts
export interface SimulationState {
  // Header
  N: number;
  step: number;
  hasResources: boolean;
  hasObstacles: boolean;

  // Agent Data
  positions: Float32Array;   // N * 3
  velocities: Float32Array;  // N * 3
  types: Uint8Array;         // N
  energies: Float32Array;    // N
  targets: Int32Array;       // N

  // Statistics
  stats: {
    meanSpeed: number;
    stdSpeed: number;
    Rg: number;
    polarization: number;
    nGroups: number;
  };

  // Resources
  resources: Array<{
    position: [number, number, number];
    amount: number;
    radius: number;
    renewable: boolean;
  }>;
}

export class BinaryDeserializer {
  static deserialize(buffer: ArrayBuffer): SimulationState {
    const view = new DataView(buffer);
    let offset = 0;

    // Header (20 bytes)
    const N = view.getUint32(offset, true); offset += 4;
    const step = view.getUint32(offset, true); offset += 4;
    const hasResources = view.getUint8(offset) === 1; offset += 1;
    const hasObstacles = view.getUint8(offset) === 1; offset += 1;
    offset += 10; // skip reserved

    // Agent Data
    const positionsLength = N * 3;
    const positions = new Float32Array(
      buffer.slice(offset, offset + positionsLength * 4)
    );
    offset += positionsLength * 4;

    const velocities = new Float32Array(
      buffer.slice(offset, offset + positionsLength * 4)
    );
    offset += positionsLength * 4;

    const types = new Uint8Array(buffer.slice(offset, offset + N));
    offset += N;

    // Skip padding
    const padding = (4 - (N % 4)) % 4;
    offset += padding;

    const energies = new Float32Array(
      buffer.slice(offset, offset + N * 4)
    );
    offset += N * 4;

    const targets = new Int32Array(
      buffer.slice(offset, offset + N * 4)
    );
    offset += N * 4;

    // Statistics (64 bytes)
    const stats = {
      meanSpeed: view.getFloat32(offset, true),
      stdSpeed: view.getFloat32(offset + 4, true),
      Rg: view.getFloat32(offset + 8, true),
      polarization: view.getFloat32(offset + 12, true),
      nGroups: view.getUint32(offset + 16, true),
    };
    offset += 64;

    // Resources (optional)
    const resources: SimulationState['resources'] = [];
    if (hasResources) {
      const nResources = view.getUint32(offset, true);
      offset += 4;

      for (let i = 0; i < nResources; i++) {
        const x = view.getFloat32(offset, true); offset += 4;
        const y = view.getFloat32(offset, true); offset += 4;
        const z = view.getFloat32(offset, true); offset += 4;
        const amount = view.getFloat32(offset, true); offset += 4;
        const radius = view.getFloat32(offset, true); offset += 4;
        const renewable = view.getUint8(offset) === 1; offset += 1;
        offset += 3; // skip padding

        resources.push({
          position: [x, y, z],
          amount,
          radius,
          renewable,
        });
      }
    }

    return {
      N,
      step,
      hasResources,
      hasObstacles,
      positions,
      velocities,
      types,
      energies,
      targets,
      stats,
      resources,
    };
  }
}
```

---

### 2. 參數更新請求（Frontend → Backend）

**資料結構**（JSON 格式，低頻更新）:

```typescript
// frontend/src/types/params.ts
export interface SimulationParams {
  // System Config
  systemType: '2D' | '3D' | 'Heterogeneous';
  N: number;
  
  // Physics
  Ca: number;    // Morse attraction
  Cr: number;    // Morse repulsion
  la: number;
  lr: number;
  rc: number;
  alpha: number; // Rayleigh friction
  v0: number;
  beta: number;  // Alignment
  eta: number;   // Noise
  boxSize: number;
  boundaryMode: 'pbc' | 'reflective' | 'absorbing';
  
  // Heterogeneity (optional)
  agentConfig?: {
    explorerRatio: number;
    followerRatio: number;
    leaderRatio: number;
    enableFov: boolean;
    fovAngle: number;
    enableGoals: boolean;
    goalPosition: [number, number, number];
  };
  
  // Resources (optional)
  resources?: Array<{
    position: [number, number, number];
    amount: number;
    radius: number;
    renewable: boolean;
    replenishRate?: number;
    maxAmount?: number;
  }>;
}

export interface ControlCommand {
  type: 'start' | 'pause' | 'reset' | 'update_params';
  payload?: SimulationParams;
}
```

**WebSocket 通訊協定**:

```
Client → Server:
  {
    "type": "update_params",
    "payload": { ...SimulationParams }
  }
  
  {
    "type": "start"
  }
  
  {
    "type": "pause"
  }
  
  {
    "type": "reset"
  }

Server → Client:
  - Binary data (每幀模擬狀態)
  - JSON messages (控制回應、錯誤訊息)
    {
      "type": "info",
      "message": "System created successfully"
    }
    
    {
      "type": "error",
      "message": "Invalid parameters"
    }
```

---

## 🚀 實作計畫（3 週）

### Week 1: Backend 實作 + 資料層

#### Day 1-2: WebSocket Server 基礎架構
**目標**: 建立 WebSocket 伺服器與基本通訊

**檔案**:
```
backend/
├── server.py           # WebSocket 伺服器主程式
├── serializer.py       # 二進位序列化器
├── simulation_manager.py  # 模擬管理器
└── requirements.txt    # 依賴套件
```

**實作**:
```python
# backend/server.py
import asyncio
import websockets
import json
from simulation_manager import SimulationManager
from serializer import BinarySerializer

class FlockingServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.manager = SimulationManager()
        self.running = False
        
    async def handle_client(self, websocket):
        """處理客戶端連線"""
        print(f"Client connected: {websocket.remote_address}")
        
        try:
            # 監聽控制訊息
            async def listen_commands():
                async for message in websocket:
                    await self.handle_command(websocket, message)
            
            # 推送模擬狀態
            async def push_state():
                while self.running:
                    if self.manager.system:
                        # 執行一幀
                        self.manager.step()
                        
                        # 序列化並傳送
                        data = BinarySerializer.serialize_state(self.manager.system)
                        await websocket.send(data)
                    
                    await asyncio.sleep(0.016)  # ~60 FPS
            
            # 同時執行兩個任務
            await asyncio.gather(
                listen_commands(),
                push_state()
            )
            
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {websocket.remote_address}")
    
    async def handle_command(self, websocket, message):
        """處理控制命令"""
        try:
            cmd = json.loads(message)
            cmd_type = cmd.get('type')
            
            if cmd_type == 'update_params':
                params = cmd.get('payload')
                self.manager.update_params(params)
                await websocket.send(json.dumps({
                    'type': 'info',
                    'message': 'Parameters updated'
                }))
                
            elif cmd_type == 'start':
                self.running = True
                await websocket.send(json.dumps({
                    'type': 'info',
                    'message': 'Simulation started'
                }))
                
            elif cmd_type == 'pause':
                self.running = False
                await websocket.send(json.dumps({
                    'type': 'info',
                    'message': 'Simulation paused'
                }))
                
            elif cmd_type == 'reset':
                self.manager.reset()
                await websocket.send(json.dumps({
                    'type': 'info',
                    'message': 'Simulation reset'
                }))
                
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def start(self):
        """啟動伺服器"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"Server started at ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

if __name__ == '__main__':
    server = FlockingServer()
    asyncio.run(server.start())
```

```python
# backend/simulation_manager.py
import sys
sys.path.insert(0, '../src')

import taichi as ti
from flocking_3d import Flocking3D, FlockingParams
from flocking_heterogeneous import HeterogeneousFlocking3D, AgentType
from resources import create_resource, create_renewable_resource

class SimulationManager:
    """模擬系統管理器"""
    
    def __init__(self):
        # 初始化 Taichi（只執行一次）
        ti.init(arch=ti.gpu)
        
        self.system = None
        self.params = None
        self.step_count = 0
        
    def create_system(self, params: dict):
        """創建模擬系統"""
        system_type = params.get('systemType', 'Heterogeneous')
        N = params.get('N', 100)
        
        # 建立物理參數
        flocking_params = FlockingParams(
            Ca=params.get('Ca', 1.5),
            Cr=params.get('Cr', 2.0),
            la=params.get('la', 2.5),
            lr=params.get('lr', 0.5),
            rc=params.get('rc', 15.0),
            alpha=params.get('alpha', 2.0),
            v0=params.get('v0', 1.0),
            beta=params.get('beta', 1.0),
            eta=params.get('eta', 0.0),
            box_size=params.get('boxSize', 50.0),
            boundary_mode=params.get('boundaryMode', 'pbc'),
        )
        
        # 建立系統
        if system_type == 'Heterogeneous':
            agent_config = params.get('agentConfig', {})
            explorer_ratio = agent_config.get('explorerRatio', 0.3)
            follower_ratio = agent_config.get('followerRatio', 0.5)
            
            n_explorer = int(N * explorer_ratio)
            n_follower = int(N * follower_ratio)
            n_leader = N - n_explorer - n_follower
            
            agent_types = (
                [AgentType.EXPLORER] * n_explorer +
                [AgentType.FOLLOWER] * n_follower +
                [AgentType.LEADER] * n_leader
            )
            
            self.system = HeterogeneousFlocking3D(
                N=N,
                params=flocking_params,
                agent_types=agent_types,
                enable_fov=agent_config.get('enableFov', True),
                fov_angle=agent_config.get('fovAngle', 120.0),
                max_obstacles=10,
                max_resources=5,
            )
            
            # 設定 goals
            if agent_config.get('enableGoals', False):
                goal_pos = agent_config.get('goalPosition', [10.0, 10.0, 10.0])
                leader_indices = [i for i, t in enumerate(agent_types) if t == AgentType.LEADER]
                if len(leader_indices) > 0:
                    import numpy as np
                    goals = np.tile(goal_pos, (len(leader_indices), 1))
                    self.system.set_goals(goals, leader_indices)
            
            # 新增資源
            resources = params.get('resources', [])
            for res_cfg in resources:
                pos = tuple(res_cfg['position'])
                if res_cfg.get('renewable', False):
                    res = create_renewable_resource(
                        position=pos,
                        amount=res_cfg.get('amount', 100.0),
                        radius=res_cfg.get('radius', 3.0),
                        replenish_rate=res_cfg.get('replenishRate', 2.0),
                        max_amount=res_cfg.get('maxAmount', 200.0),
                    )
                else:
                    res = create_resource(
                        position=pos,
                        amount=res_cfg.get('amount', 100.0),
                        radius=res_cfg.get('radius', 3.0),
                    )
                self.system.add_resource(res)
        
        elif system_type == '3D':
            self.system = Flocking3D(N=N, params=flocking_params)
        
        # 初始化
        self.system.initialize(box_size=flocking_params.box_size, seed=42)
        self.system.step_count = 0
        self.step_count = 0
        self.params = params
        
    def update_params(self, params: dict):
        """更新參數（重建系統）"""
        self.create_system(params)
    
    def step(self):
        """執行一幀模擬"""
        if self.system:
            self.system.step(0.05)
            self.step_count += 1
            self.system.step_count = self.step_count
    
    def reset(self):
        """重置模擬"""
        if self.params:
            self.create_system(self.params)
```

**測試**:
```bash
# 測試 WebSocket Server
cd backend
uv run python server.py

# 另一個終端機測試連線
wscat -c ws://localhost:8765
# 發送: {"type": "update_params", "payload": {"systemType": "Heterogeneous", "N": 100}}
# 發送: {"type": "start"}
```

---

#### Day 3-4: 序列化效能優化
**目標**: 優化資料傳輸，確保 60 FPS

**優化策略**:
1. **選擇性更新**: 只傳輸變化的資料
2. **壓縮**: 使用 LZ4 壓縮（可選）
3. **差分編碼**: Delta encoding（位置變化小時）

**進階序列化**:
```python
# backend/serializer.py (優化版)
import lz4.frame  # pip install lz4

class OptimizedSerializer:
    """優化版序列化器"""
    
    @staticmethod
    def serialize_state_compressed(system) -> bytes:
        """壓縮版序列化（降低 30-50% 大小）"""
        raw_data = BinarySerializer.serialize_state(system)
        compressed = lz4.frame.compress(raw_data, compression_level=1)
        return compressed
    
    @staticmethod
    def serialize_delta(system, prev_positions: np.ndarray) -> bytes:
        """差分編碼（當位置變化小時效果好）"""
        x_np = system.x.to_numpy()
        delta = (x_np - prev_positions).astype(np.float16)  # 使用 float16
        # ... 編碼 delta
```

**效能測試**:
```python
# backend/test_serializer.py
import time
import numpy as np
from serializer import BinarySerializer

# 測試序列化速度
N = 500
# ... 創建 system
iterations = 1000

start = time.time()
for _ in range(iterations):
    data = BinarySerializer.serialize_state(system)
elapsed = time.time() - start

print(f"Serialization: {iterations/elapsed:.1f} FPS")
print(f"Data size: {len(data)} bytes")
```

**目標**: Serialization > 100 FPS (保證足夠餘裕)

---

#### Day 5-7: Frontend 專案初始化 + 資料層
**目標**: 建立 React 專案，實作 WebSocket Client

**初始化專案**:
```bash
cd /Users/latteine/Documents/coding/alife
mkdir frontend
cd frontend

# 使用 Vite 創建專案（比 CRA 快 10 倍）
npm create vite@latest . -- --template react-ts

# 安裝依賴
npm install
npm install zustand           # 狀態管理
npm install @webgpu/types     # WebGPU 型別
npm install gl-matrix         # 矩陣運算
npm install @radix-ui/react-slider @radix-ui/react-select  # UI 組件（可選）

# 安裝開發工具
npm install -D @types/node
```

**目錄結構**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── ControlPanel.tsx     # 參數控制面板
│   │   ├── Statistics.tsx       # 統計資訊顯示
│   │   └── Canvas3D.tsx         # WebGPU 渲染 canvas
│   ├── lib/
│   │   ├── websocket-client.ts  # WebSocket 客戶端
│   │   ├── deserializer.ts      # 反序列化器
│   │   └── webgpu-renderer.ts   # WebGPU 渲染器（Week 2）
│   ├── store/
│   │   └── simulation-store.ts  # 全域狀態管理
│   ├── types/
│   │   ├── params.ts            # 參數型別定義
│   │   └── state.ts             # 狀態型別定義
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
└── tsconfig.json
```

**實作 WebSocket Client**:
```typescript
// frontend/src/lib/websocket-client.ts
import { BinaryDeserializer, SimulationState } from './deserializer';
import { SimulationParams, ControlCommand } from '../types/params';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onStateUpdate: ((state: SimulationState) => void) | null = null;
  private onMessage: ((message: any) => void) | null = null;

  constructor(url: string = 'ws://localhost:8765') {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Binary data (simulation state)
          const state = BinaryDeserializer.deserialize(event.data);
          this.onStateUpdate?.(state);
        } else {
          // JSON message (control response)
          const message = JSON.parse(event.data);
          this.onMessage?.(message);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
      };
    });
  }

  disconnect() {
    this.ws?.close();
  }

  sendCommand(command: ControlCommand) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }
    this.ws.send(JSON.stringify(command));
  }

  updateParams(params: SimulationParams) {
    this.sendCommand({ type: 'update_params', payload: params });
  }

  start() {
    this.sendCommand({ type: 'start' });
  }

  pause() {
    this.sendCommand({ type: 'pause' });
  }

  reset() {
    this.sendCommand({ type: 'reset' });
  }

  setOnStateUpdate(callback: (state: SimulationState) => void) {
    this.onStateUpdate = callback;
  }

  setOnMessage(callback: (message: any) => void) {
    this.onMessage = callback;
  }
}
```

**實作狀態管理**:
```typescript
// frontend/src/store/simulation-store.ts
import { create } from 'zustand';
import { SimulationState } from '../lib/deserializer';
import { SimulationParams } from '../types/params';
import { WebSocketClient } from '../lib/websocket-client';

interface SimulationStore {
  // State
  state: SimulationState | null;
  params: SimulationParams;
  isConnected: boolean;
  isRunning: boolean;
  
  // WebSocket client
  client: WebSocketClient;
  
  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  updateParams: (params: Partial<SimulationParams>) => void;
  start: () => void;
  pause: () => void;
  reset: () => void;
  setState: (state: SimulationState) => void;
}

const defaultParams: SimulationParams = {
  systemType: 'Heterogeneous',
  N: 100,
  Ca: 1.5,
  Cr: 2.0,
  la: 2.5,
  lr: 0.5,
  rc: 15.0,
  alpha: 2.0,
  v0: 1.0,
  beta: 1.0,
  eta: 0.0,
  boxSize: 50.0,
  boundaryMode: 'pbc',
  agentConfig: {
    explorerRatio: 0.3,
    followerRatio: 0.5,
    leaderRatio: 0.2,
    enableFov: true,
    fovAngle: 120,
    enableGoals: false,
    goalPosition: [10, 10, 10],
  },
};

export const useSimulationStore = create<SimulationStore>((set, get) => {
  const client = new WebSocketClient();
  
  // 設定回調
  client.setOnStateUpdate((state) => {
    set({ state });
  });
  
  client.setOnMessage((message) => {
    console.log('Server message:', message);
  });
  
  return {
    state: null,
    params: defaultParams,
    isConnected: false,
    isRunning: false,
    client,
    
    connect: async () => {
      try {
        await client.connect();
        set({ isConnected: true });
        
        // 初始化系統
        client.updateParams(get().params);
      } catch (error) {
        console.error('Failed to connect:', error);
      }
    },
    
    disconnect: () => {
      client.disconnect();
      set({ isConnected: false, isRunning: false });
    },
    
    updateParams: (newParams) => {
      const updatedParams = { ...get().params, ...newParams };
      set({ params: updatedParams });
      client.updateParams(updatedParams);
    },
    
    start: () => {
      client.start();
      set({ isRunning: true });
    },
    
    pause: () => {
      client.pause();
      set({ isRunning: false });
    },
    
    reset: () => {
      client.reset();
      set({ isRunning: false });
    },
    
    setState: (state) => {
      set({ state });
    },
  };
});
```

**Week 1 檢查點**:
- [ ] WebSocket Server 正常運作
- [ ] 序列化速度 > 100 FPS
- [ ] Frontend 能連線並接收資料
- [ ] 參數更新能觸發系統重建
- [ ] 基本 UI 框架完成

---

### Week 2: WebGPU 渲染引擎

*(詳細實作見下一節，內容過長)*

---

### Week 3: UI 整合 + 優化

*(詳細實作見下一節)*

---

## 📝 開發檢查清單

### 必要功能 (Must Have)
- [ ] WebSocket 通訊建立
- [ ] 二進位序列化/反序列化
- [ ] WebGPU 基本渲染（粒子系統）
- [ ] 參數控制面板
- [ ] 即時統計顯示
- [ ] 相機控制（旋轉/縮放/平移）

### 重要功能 (Should Have)
- [ ] 資源球體渲染
- [ ] 能量著色
- [ ] 速度向量顯示
- [ ] 效能優化（60 FPS @ N=500）

### 可選功能 (Nice to Have)
- [ ] 時間序列圖表
- [ ] 截圖/錄影
- [ ] 預設配置快速載入
- [ ] 鍵盤快捷鍵

---

**下一步**: 我準備繼續寫 Week 2 和 Week 3 的詳細實作。需要我繼續嗎？還是你想先看看這個架構設計是否符合你的需求？

**注意**: 完整文件會非常長（預計 2000+ 行），我建議分多個檔案：
1. `WEBGPU_INTEGRATION_PLAN.md` (本檔案，架構設計)
2. `WEBGPU_WEEK2_RENDERING.md` (Week 2 詳細實作)
3. `WEBGPU_WEEK3_UI.md` (Week 3 詳細實作)
4. `WEBGPU_TROUBLESHOOTING.md` (常見問題與除錯)

是否繼續？
