# ALife 3D Flocking

基於 Taichi 的 2D/3D 群聚（flocking）與異質生態系統模擬專案。

- 核心引擎：Morse potential + Rayleigh friction + Cucker-Smale alignment
- 生態行為：foraging / predation / reproduction（持續整合）
- 系統架構：Mixin 組合式設計，便於擴充與測試
- 介面整合：Python WebSocket backend + React/WebGPU frontend（進行中）

---

## 專案目前狀態

- 核心模擬與異質行為可運行
- 測試分層為 `tests/`、`tests/grid/`、`tests/integration/`
- 文件已集中於 `docs/`（含 `archive/`、`reports/`、`status/`、`plans/`）

---

## 快速開始

### 1) 安裝依賴

```bash
# 建議：在專案根目錄
uv pip install -e .
```

常用額外套件（視需求）：

```bash
uv pip install matplotlib pytest
```

### 2) 執行展示

```bash
# 3D 基礎 flocking
uv run python experiments/demo_3d.py

# 2D 基礎 flocking
uv run python experiments/demo_2d.py

# 異質生態（覓食/捕食）
uv run python experiments/demo_heterogeneous.py
uv run python experiments/demo_foraging.py

# 其他場景
uv run python experiments/demo_group_detection.py
uv run python experiments/demo_obstacles.py
```

### 3) 執行測試

```bash
# 全部測試
uv run pytest tests/ -q

# 指定模組
uv run pytest tests/test_physics.py -v
uv run pytest tests/test_heterogeneous.py -v
uv run pytest tests/integration/ -v
```

---

## 核心架構

`src/flocking_heterogeneous.py` 為主協調器，透過 mixin 串接能力模組：

- `src/spatial/grid.py`：空間網格加速（neighbor search）
- `src/spatial/group_detection.py`：群組偵測
- `src/behaviors/foraging.py`：覓食與能量系統
- `src/behaviors/predation.py`：捕食與生死機制
- `src/behaviors/reproduction.py`：繁殖演化（WIP）
- `src/perception/fov.py`：FOV 感知過濾
- `src/navigation/goal_seeking.py`：目標導向導航

核心數值引擎：

- `src/flocking_2d.py`
- `src/flocking_3d.py`
- `src/flocking_celllist.py`

---

## 目錄導覽

```text
alife/
├── src/                 # 模擬核心
├── tests/               # 單元與整合測試
├── experiments/         # 可執行示例
├── backend/             # WebSocket 後端
├── frontend/            # React + WebGPU 前端
├── configs/             # YAML 實驗設定
└── docs/                # 技術文件與報告
```

---

## Backend / Frontend

### Backend

```bash
cd backend
uv pip install -r requirements.txt
uv run python server.py
```

更多資訊見：`backend/README.md`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 重要文件

- `docs/GUIDE.md`：使用指南
- `docs/API.md`：API 參考
- `docs/CHANGELOG.md`：版本歷史
- `docs/WEBGPU_INTEGRATION_PLAN.md`：前端整合規劃
- `AGENTS.md`：專案開發規範

---

## 授權

MIT License
