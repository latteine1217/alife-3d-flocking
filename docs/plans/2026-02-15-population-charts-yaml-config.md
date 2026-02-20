# Population Charts & YAML Config Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 擴充 `SystemBalanceCharts.tsx` 加入完整族群動態指標（各類型數量、飢餓率、Lotka-Volterra 比、群組數），並建立 YAML 實驗設定檔系統。

**Architecture:**
- 前端：擴充現有 `BalanceSample` 介面加入缺少的指標欄位，新增對應 `LineChartCard`；並修正 `AgentType` 常數缺少 `PREDATOR=3` 的問題。
- 後端：新增 `configs/` 目錄與 YAML Loader（`src/config.py`），`backend/server.py` 支援 `--config` 啟動參數；新增 WebSocket 命令 `load_config` 讓前端可切換實驗設定。

**Tech Stack:** TypeScript (React, SVG), Python (PyYAML, argparse)

---

## Task 1：修正前端 AgentType 常數，加入 PREDATOR

**Files:**
- Modify: `frontend/src/types/simulation.ts:111-115`

### Step 1：直接修改 AgentType 常數

在 `simulation.ts` 的 `AgentType` 物件加入 `PREDATOR: 3`：

```typescript
export const AgentType = {
  FOLLOWER: 0,
  EXPLORER: 1,
  LEADER: 2,
  PREDATOR: 3,
} as const;
```

### Step 2：確認前端能 build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: 無 TypeScript 錯誤。

### Step 3：Commit

```bash
git add frontend/src/types/simulation.ts
git commit -m "fix(frontend): add PREDATOR=3 to AgentType constants"
```

---

## Task 2：擴充 BalanceSample 並計算新指標

**Files:**
- Modify: `frontend/src/components/SystemBalanceCharts.tsx:1-65`

### 背景知識

- `state.types: Uint8Array` — 每個 alive agent 的類型（0=Follower, 1=Explorer, 2=Leader, 3=Predator）
- `state.energies: Float32Array` — 每個 alive agent 的能量值
- `state.stats.nGroups: number` — 當前活躍群組數
- `state.resources: Array<{amount: number}>` — 每個資源的 amount ratio (0-1)
- "飢餓"定義：能量 < 30（對應後端 `energy_threshold=30.0`）

### Step 1：擴充 BalanceSample 介面

將現有介面替換為：

```typescript
interface BalanceSample {
  step: number;
  // 族群數量
  totalAlive: number;
  explorerCount: number;
  followerCount: number;
  predatorCount: number;
  // 生態指標
  hungerRatio: number;      // 飢餓 agents / 總存活
  lotkaVolterra: number;    // predators / non-predators (0 if no prey)
  nGroups: number;
  // 能量系統
  predatorEnergy: number;
  resourceEnergy: number;
  totalEnergy: number;
}
```

### Step 2：更新 useEffect 計算邏輯

替換現有計算 block（第 18-65 行）：

```typescript
useEffect(() => {
  if (!state) return;

  const HUNGER_THRESHOLD = 30.0;

  let explorerCount = 0;
  let followerCount = 0;
  let predatorCount = 0;
  let predatorEnergy = 0;
  let nonPredatorEnergy = 0;
  let maxAgentEnergy = 1;
  let hungryCount = 0;

  for (let i = 0; i < state.energies.length; i++) {
    const e = state.energies[i];
    const t = state.types[i];
    if (e > maxAgentEnergy) maxAgentEnergy = e;
    if (e < HUNGER_THRESHOLD) hungryCount++;

    if (t === 3) { // PREDATOR
      predatorCount++;
      predatorEnergy += e;
    } else {
      nonPredatorEnergy += e;
      if (t === 0) followerCount++;
      else if (t === 1) explorerCount++;
    }
  }

  const totalAlive = state.energies.length;
  const hungerRatio = totalAlive > 0 ? hungryCount / totalAlive : 0;
  const preyCount = totalAlive - predatorCount;
  const lotkaVolterra = preyCount > 0 ? predatorCount / preyCount : 0;

  let resourceRatioSum = 0;
  for (let i = 0; i < state.resources.length; i++) {
    resourceRatioSum += state.resources[i].amount;
  }
  const resourceEnergy = resourceRatioSum * maxAgentEnergy;
  const totalEnergy = nonPredatorEnergy + predatorEnergy + resourceEnergy;

  const nextSample: BalanceSample = {
    step: state.step,
    totalAlive,
    explorerCount,
    followerCount,
    predatorCount,
    hungerRatio,
    lotkaVolterra,
    nGroups: state.stats.nGroups,
    predatorEnergy,
    resourceEnergy,
    totalEnergy,
  };

  setHistory((prev) => {
    if (prev.length > 0 && prev[prev.length - 1].step === nextSample.step) {
      return prev;
    }
    const next = [...prev, nextSample];
    if (next.length > MAX_POINTS) next.shift();
    return next;
  });
}, [state]);
```

### Step 3：確認前端能 build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: 無錯誤。

### Step 4：Commit

```bash
git add frontend/src/components/SystemBalanceCharts.tsx
git commit -m "feat(charts): extend BalanceSample with population breakdown metrics"
```

---

## Task 3：新增圖表卡片顯示所有新指標

**Files:**
- Modify: `frontend/src/components/SystemBalanceCharts.tsx:75-106`（JSX return block）

### Step 1：更新 JSX，加入新圖表

將現有 `return` block 替換為（`latest` 宣告也要更新欄位名稱）：

```tsx
const latest = history.length > 0 ? history[history.length - 1] : null;

return (
  <section className="balance-panel">
    <div className="balance-header">
      <h2>System Balance</h2>
      <p>Realtime trends for population and energy budget</p>
    </div>

    {history.length < 2 ? (
      <div className="balance-empty">Waiting for enough frames to draw charts...</div>
    ) : (
      <>
        <div className="balance-grid">
          <LineChartCard
            title="Total Alive"
            unit="agents"
            color="#27d3a2"
            samples={history}
            valueAccessor={(s) => s.totalAlive}
            latestValue={latest?.totalAlive ?? 0}
          />
          <LineChartCard
            title="Explorer Count"
            unit="agents"
            color="#58c4e0"
            samples={history}
            valueAccessor={(s) => s.explorerCount}
            latestValue={latest?.explorerCount ?? 0}
          />
          <LineChartCard
            title="Follower Count"
            unit="agents"
            color="#a0c878"
            samples={history}
            valueAccessor={(s) => s.followerCount}
            latestValue={latest?.followerCount ?? 0}
          />
          <LineChartCard
            title="Predator Count"
            unit="agents"
            color="#e05c5c"
            samples={history}
            valueAccessor={(s) => s.predatorCount}
            latestValue={latest?.predatorCount ?? 0}
          />
        </div>

        <div className="balance-grid">
          <LineChartCard
            title="Hunger Ratio"
            unit="%"
            color="#ffb347"
            samples={history}
            valueAccessor={(s) => s.hungerRatio * 100}
            latestValue={(latest?.hungerRatio ?? 0) * 100}
          />
          <LineChartCard
            title="Predator / Prey"
            unit="ratio"
            color="#c084e0"
            samples={history}
            valueAccessor={(s) => s.lotkaVolterra}
            latestValue={latest?.lotkaVolterra ?? 0}
          />
          <LineChartCard
            title="Active Groups"
            unit="groups"
            color="#60b0f4"
            samples={history}
            valueAccessor={(s) => s.nGroups}
            latestValue={latest?.nGroups ?? 0}
          />
          <LineChartCard
            title="Total System Energy"
            unit="energy"
            color="#ffb347"
            samples={history}
            valueAccessor={(s) => s.totalEnergy}
            latestValue={latest?.totalEnergy ?? 0}
          />
        </div>
      </>
    )}
  </section>
);
```

### Step 2：確認前端能 build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: 無錯誤。

### Step 3：在瀏覽器確認圖表顯示

啟動後端與前端後，觀察 System Balance 區塊是否出現 8 張圖表（2 排 × 4 個）。

### Step 4：Commit

```bash
git add frontend/src/components/SystemBalanceCharts.tsx
git commit -m "feat(charts): add per-type counts, hunger ratio, Lotka-Volterra, group count charts"
```

---

## Task 4：新增 CSS grid 支援兩排圖表佈局

**Files:**
- Modify: `frontend/src/App.css`（搜尋 `.balance-grid`）

### Step 1：確認現有 `.balance-grid` 樣式

```bash
grep -n "balance-grid\|balance-panel" frontend/src/App.css
```

### Step 2：確認兩個 `.balance-grid` 在不同 `<div>` 下皆可正確渲染

若 `.balance-grid` 已是 CSS grid 4 欄，Task 3 的 JSX 應可直接運作。若不是，修改為：

```css
.balance-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
```

### Step 3：Commit（若有變動）

```bash
git add frontend/src/App.css
git commit -m "style(charts): ensure balance-grid supports two rows of 4 charts"
```

---

## Task 5：建立 YAML 設定檔系統

**Files:**
- Create: `configs/default.yaml`
- Create: `configs/predator_heavy.yaml`
- Create: `configs/foraging_only.yaml`
- Create: `src/config.py`

### 背景知識

後端 `SimulationManager.__init__()` 的 `default_params` dict 定義了所有可調參數，鍵名對應前端的 `SimulationParams` 介面。YAML 設定檔只需定義要覆蓋的欄位。

### Step 1：安裝 PyYAML

```bash
uv pip install pyyaml
```

確認：`uv run python -c "import yaml; print(yaml.__version__)"`

### Step 2：建立 `configs/default.yaml`

```yaml
# Default experiment: balanced predator-prey ecosystem
meta:
  name: "Default Balanced"
  description: "平衡的捕食者-獵物生態系統，適合基礎觀察"

simulation:
  N: 100
  Ca: 1.5
  Cr: 2.0
  la: 2.5
  lr: 0.5
  rc: 15.0
  alpha: 2.0
  v0: 1.0
  beta: 1.0
  eta: 0.0
  boxSize: 50.0
  boundaryMode: "pbc"

agents:
  explorerRatio: 0.3
  followerRatio: 0.5
  predatorRatio: 0.05
  enableFov: true
  fovAngle: 120.0

resources:
  - position: [16.0, 14.0, 15.0]
    amount: 280.0
    radius: 5.5
    renewable: true
    replenishRate: 90.0
    maxAmount: 420.0
  - position: [-17.0, 15.0, -14.0]
    amount: 260.0
    radius: 5.0
    renewable: true
    replenishRate: 85.0
    maxAmount: 380.0
  - position: [14.0, -16.0, -13.0]
    amount: 250.0
    radius: 4.8
    renewable: true
    replenishRate: 80.0
    maxAmount: 360.0
```

### Step 3：建立 `configs/predator_heavy.yaml`

```yaml
meta:
  name: "Predator Heavy"
  description: "高捕食者密度：測試族群崩潰與恢復動態"

simulation:
  N: 120
  Ca: 1.5
  Cr: 2.0
  la: 2.5
  lr: 0.5
  rc: 15.0
  alpha: 2.0
  v0: 1.2
  beta: 1.0
  eta: 0.05
  boxSize: 50.0
  boundaryMode: "pbc"

agents:
  explorerRatio: 0.3
  followerRatio: 0.5
  predatorRatio: 0.15
  enableFov: true
  fovAngle: 120.0

resources:
  - position: [16.0, 14.0, 15.0]
    amount: 300.0
    radius: 6.0
    renewable: true
    replenishRate: 120.0
    maxAmount: 500.0
  - position: [-17.0, 15.0, -14.0]
    amount: 300.0
    radius: 6.0
    renewable: true
    replenishRate: 120.0
    maxAmount: 500.0
```

### Step 4：建立 `configs/foraging_only.yaml`

```yaml
meta:
  name: "Foraging Only"
  description: "無捕食者：純覓食動態，觀察資源枯竭與能量平衡"

simulation:
  N: 80
  Ca: 1.5
  Cr: 2.0
  la: 2.5
  lr: 0.5
  rc: 15.0
  alpha: 2.0
  v0: 1.0
  beta: 1.2
  eta: 0.0
  boxSize: 40.0
  boundaryMode: "pbc"

agents:
  explorerRatio: 0.4
  followerRatio: 0.6
  predatorRatio: 0.0
  enableFov: true
  fovAngle: 150.0

resources:
  - position: [10.0, 10.0, 10.0]
    amount: 400.0
    radius: 7.0
    renewable: true
    replenishRate: 60.0
    maxAmount: 600.0
  - position: [-10.0, -10.0, -10.0]
    amount: 400.0
    radius: 7.0
    renewable: true
    replenishRate: 60.0
    maxAmount: 600.0
```

### Step 5：建立 `src/config.py`

```python
"""
YAML 實驗設定檔載入器

What: 讀取 YAML 設定檔，轉換為 backend SimulationManager 接受的 params dict
Why: 讓不同實驗場景可重現，避免參數散落在程式碼中
"""

import yaml
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path(__file__).parent.parent / "configs"


def load_config(name: str) -> dict:
    """
    載入指定名稱的實驗設定檔（不含 .yaml 副檔名）
    例如: load_config("default") 讀取 configs/default.yaml
    """
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _to_params(raw)


def list_configs() -> list[str]:
    """列出所有可用的設定檔名稱（不含副檔名）"""
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


def _to_params(raw: dict) -> dict:
    """
    將 YAML 結構轉換為 SimulationManager 接受的 params dict
    格式與 backend/simulation_manager.py 的 default_params 一致
    """
    sim = raw.get("simulation", {})
    agents = raw.get("agents", {})
    resources_raw = raw.get("resources", [])

    resources = []
    for r in resources_raw:
        res = {
            "position": r["position"],
            "amount": r["amount"],
            "radius": r["radius"],
            "renewable": r.get("renewable", True),
        }
        if r.get("renewable", True):
            res["replenishRate"] = r.get("replenishRate", 50.0)
            res["maxAmount"] = r.get("maxAmount", r["amount"] * 2)
        resources.append(res)

    params = {
        "systemType": "Heterogeneous",
        "N": sim.get("N", 100),
        "Ca": sim.get("Ca", 1.5),
        "Cr": sim.get("Cr", 2.0),
        "la": sim.get("la", 2.5),
        "lr": sim.get("lr", 0.5),
        "rc": sim.get("rc", 15.0),
        "alpha": sim.get("alpha", 2.0),
        "v0": sim.get("v0", 1.0),
        "beta": sim.get("beta", 1.0),
        "eta": sim.get("eta", 0.0),
        "boxSize": sim.get("boxSize", 50.0),
        "boundaryMode": sim.get("boundaryMode", "pbc"),
        "agentConfig": {
            "explorerRatio": agents.get("explorerRatio", 0.3),
            "followerRatio": agents.get("followerRatio", 0.5),
            "predatorRatio": agents.get("predatorRatio", 0.05),
            "enableFov": agents.get("enableFov", True),
            "fovAngle": agents.get("fovAngle", 120.0),
        },
        "resources": resources,
    }
    return params
```

### Step 6：為 `config.py` 寫測試

```python
# tests/test_config.py
import pytest
from src.config import load_config, list_configs, _to_params


def test_list_configs_returns_yaml_names():
    names = list_configs()
    assert "default" in names
    assert "predator_heavy" in names
    assert "foraging_only" in names


def test_load_config_default():
    params = load_config("default")
    assert params["N"] == 100
    assert params["systemType"] == "Heterogeneous"
    assert "agentConfig" in params
    assert len(params["resources"]) > 0


def test_load_config_predator_heavy():
    params = load_config("predator_heavy")
    assert params["agentConfig"]["predatorRatio"] == 0.15


def test_load_config_foraging_only():
    params = load_config("foraging_only")
    assert params["agentConfig"]["predatorRatio"] == 0.0


def test_load_config_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config_xyz")


def test_to_params_resource_defaults():
    raw = {
        "simulation": {"N": 50},
        "resources": [{"position": [0, 0, 0], "amount": 100.0, "radius": 3.0, "renewable": True}],
    }
    params = _to_params(raw)
    r = params["resources"][0]
    assert r["renewable"] is True
    assert "replenishRate" in r
    assert "maxAmount" in r
```

### Step 7：跑測試確認通過

```bash
uv run python -m pytest tests/test_config.py -v
```

Expected: 6 passed

### Step 8：Commit

```bash
git add configs/ src/config.py tests/test_config.py
git commit -m "feat(config): add YAML experiment config system with 3 presets"
```

---

## Task 6：整合 YAML config 到 backend server 啟動參數

**Files:**
- Modify: `backend/server.py`（加入 `--config` argparse）
- Modify: `backend/simulation_manager.py`（接受 override params）

### 背景知識

`backend/server.py` 是啟動入口。`SimulationManager` 在 `__init__` 時建立 `default_params`，之後的 `create_system(params)` 使用傳入的 params dict。

### Step 1：確認 server.py 的啟動方式

```bash
head -40 backend/server.py
```

### Step 2：在 server.py 加入 `--config` 參數

在 `if __name__ == "__main__":` block 加入：

```python
import argparse
import sys
sys.path.insert(0, "../src")

from config import load_config, list_configs

parser = argparse.ArgumentParser(description="ALife WebSocket Server")
parser.add_argument("--config", type=str, default=None,
                    help=f"實驗設定檔名稱（不含 .yaml）。可用: {list_configs()}")
args = parser.parse_args()

if args.config:
    override_params = load_config(args.config)
    print(f"[Server] 載入設定檔: {args.config}")
else:
    override_params = None
```

並在建立 `SimulationManager` 時傳入：

```python
manager = SimulationManager(initial_config=override_params)
```

### Step 3：修改 SimulationManager.__init__ 接受 initial_config

在 `__init__` 加入參數：

```python
def __init__(self, initial_config: dict | None = None):
    ...
    # 若有外部設定檔，覆蓋 default_params
    if initial_config is not None:
        self.default_params = initial_config
```

### Step 4：驗證啟動

```bash
cd backend && uv run python server.py --config predator_heavy 2>&1 | head -10
```

Expected: `[Server] 載入設定檔: predator_heavy` 且模擬正常啟動。

### Step 5：Commit

```bash
git add backend/server.py backend/simulation_manager.py
git commit -m "feat(backend): add --config CLI argument to load YAML experiment presets"
```

---

## 完成驗收

1. 前端 System Balance 區塊顯示 8 張圖表（2 排）
2. 各類型 Agent 數量隨模擬變化（捕食者數減少時獵物數增加）
3. Hunger Ratio 在資源枯竭時上升
4. `uv run python -m pytest tests/test_config.py -v` — 6 passed
5. `cd backend && uv run python server.py --config predator_heavy` 正常啟動

---

*Last updated: 2026-02-15*
