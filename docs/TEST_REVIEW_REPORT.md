# 測試檔案評估報告 (Test Suite Review)

**評估日期**: 2026-02-07  
**專案**: Heterogeneous 3D Flocking System  
**測試檔案數量**: 8 個測試檔案  
**總測試行數**: ~2,626 lines

---

## 執行摘要

### 總體評估

| 評估項目 | 狀態 | 說明 |
|---------|------|------|
| **測試層級分佈** | ⚠️ 良好但可改善 | 缺少明確的 integration/E2E 分層 |
| **核心邏輯覆蓋** | ✅ 優秀 | 物理引擎、行為系統皆有完整測試 |
| **回歸保護** | ✅ 優秀 | 已修復的 bug 有對應測試 |
| **可維護性** | ⚠️ 良好 | 部分測試過度依賴具體實作細節 |
| **CI 友善度** | ✅ 良好 | 大部分測試快速穩定 |

---

## 詳細分析

### A. 按測試層級分類

#### ✅ **Unit Tests（單元測試）** - 應長期保留

這些測試覆蓋核心邏輯，快速、穩定、價值最高。

##### 1. `test_physics.py` (507 lines) ⭐⭐⭐⭐⭐

**測試內容**:
- Morse potential 計算正確性
- Cucker-Smale alignment (含已修復的 bug regression)
- Rayleigh friction 定速機制
- PBC 距離計算
- 2D vs 3D 一致性

**評估**:
- ✅ **必須長期保留**
- ✅ 測試「純函數行為」而非實作細節
- ✅ 涵蓋邊界條件（短距、長距、PBC wrap）
- ✅ 包含 regression test (Cucker-Smale bug fix)
- ✅ 快速執行（無外部依賴）

**建議**:
```python
# ✅ GOOD: 測試可觀察行為
def test_morse_force_repulsion_at_short_range():
    """短距離應該產生排斥力"""
    # 測試輸出行為，不測內部實作

# ✅ GOOD: Regression test
def test_cucker_smale_alignment_bug_fix():
    """驗證 CS alignment 修正（2026-02-05）"""
    # 鎖住已修復的 bug
```

**保留理由**: 
- 核心物理引擎的正確性保證
- 修改物理模型時的安全網
- 跨維度一致性驗證（2D vs 3D）

---

##### 2. `test_perception.py` (187 lines) ⭐⭐⭐⭐⭐

**測試內容**:
- FOV 90°/120° 角度檢測
- 前方/後方/側面視野判斷
- FOV 啟用/停用切換
- 邊界條件（零速度、indexed 方法）

**評估**:
- ✅ **必須長期保留**
- ✅ 100% 覆蓋 PerceptionMixin API
- ✅ 測試行為而非實作（角度檢測結果）
- ✅ 清晰的測試結構（3 個測試類別）
- ✅ 快速執行（< 5 秒）

**範例**:
```python
class TestFOVBasic:
    """基本 FOV 功能測試"""
    
    def test_fov_90_degree_front(self):
        """90度視野：應該能看到正前方的 agent"""
        # ✅ 測試可觀察行為（視野內/外）

class TestFOVEdgeCases:
    """邊界情況測試"""
    
    def test_zero_velocity(self):
        """零速度時，FOV 應該退化為全向可見"""
        # ✅ 邊界條件測試
```

**保留理由**:
- Phase 6.1 新增功能的保護
- 防止未來重構破壞 FOV 邏輯
- 邊界條件完整覆蓋

---

##### 3. `test_heterogeneous.py` (421 lines) ⭐⭐⭐⭐⭐

**測試內容**:
- Agent 類型系統（FOLLOWER/EXPLORER/LEADER/PREDATOR）
- 個體參數（beta, eta, v0, mass）
- 目標導向行為（goal seeking）
- 視野限制（FOV）
- 向後相容性（homogeneous fallback）

**評估**:
- ✅ **必須長期保留**
- ✅ 測試核心異質性邏輯
- ✅ 包含向後相容性測試（critical）
- ✅ 測試行為收斂（而非瞬間狀態）

**範例**:
```python
def test_homogeneous_fallback():
    """向後相容：只用 FOLLOWER 應該退化為均質系統"""
    # ✅ 對外契約測試（向後相容性）

def test_individual_speed_convergence():
    """個體速度應該收斂到各自的 v0"""
    # ✅ 測試行為而非瞬間狀態
```

**保留理由**:
- 核心異質性功能的保證
- 向後相容性（對外契約）
- 防止參數系統回歸

---

##### 4. `test_group_detection.py` (343 lines) ⭐⭐⭐⭐

**測試內容**:
- Label Propagation 群組偵測
- 單一/多群組分離
- 速度方向聚類
- 群組統計（centroid, velocity）
- PBC 下的群組偵測

**評估**:
- ✅ **必須長期保留**
- ✅ 測試演算法正確性
- ⚠️ 部分測試依賴具體迭代次數（過度耦合實作）

**範例**:
```python
def test_single_group_detection():
    """密集且速度對齊的 agents 應形成單一群組"""
    # ✅ 測試可觀察行為

def test_velocity_direction_clustering():
    """速度方向差異應分離群組"""
    # ✅ 測試演算法邏輯
```

**⚠️ 潛在問題**:
```python
# 某些測試可能過度依賴迭代次數
for _ in range(10):  # 固定迭代次數
    system.detect_groups_iteration(...)

# 建議改為：測試收斂結果而非固定步數
```

**保留理由**:
- 群組偵測是核心功能
- Label Propagation 演算法的正確性保證

**改善建議**:
- 將「迭代次數」改為「收斂條件」
- 避免依賴具體實作細節

---

##### 5. `test_foraging.py` (319 lines) ⭐⭐⭐⭐

**測試內容**:
- 資源創建與配置
- 資源消耗機制
- 資源再生（renewable）
- 能量管理（depletion）
- 多 agent 競爭
- PBC 下的覓食

**評估**:
- ✅ **必須長期保留**
- ✅ 測試完整覓食週期（creation → consumption → regeneration）
- ✅ 邊界條件（能量耗盡、資源耗盡）
- ✅ 整合測試（與 flocking 系統互動）

**範例**:
```python
def test_full_foraging_cycle():
    """完整覓食週期：搜尋→接近→消耗→再生"""
    # ✅ 整合測試（多階段流程）

def test_energy_depletion():
    """能量耗盡應觸發死亡或停止行為"""
    # ✅ 邊界條件測試
```

**保留理由**:
- 覓食系統的正確性保證
- 生態模擬的關鍵功能

---

##### 6. `test_obstacles.py` (336 lines) ⭐⭐⭐⭐

**測試內容**:
- SDF (Signed Distance Field) 計算
- 障礙物排斥力
- 與 flocking 系統整合
- 動態障礙物
- 複雜場景（走廊導航）

**評估**:
- ✅ **必須長期保留**
- ✅ 測試 SDF 數學正確性
- ✅ 整合測試（障礙物 + flocking）
- ⚠️ 部分測試可能執行較慢（走廊導航）

**範例**:
```python
def test_sphere_sdf():
    """球體 SDF 應正確計算距離"""
    # ✅ 數學正確性測試

def test_corridor_navigation():
    """agents 應能穿越走廊而不穿牆"""
    # ✅ 實際應用場景測試
```

**保留理由**:
- SDF 數學正確性
- 障礙物系統的基礎保證

**改善建議**:
- 將慢速測試標記為 `@pytest.mark.slow`
- CI 可選擇性執行

---

#### ⚠️ **Integration Tests（整合測試）** - 部分可優化

##### 7. `test_advanced_physics.py` (226 lines) ⭐⭐⭐

**測試內容**:
- Vicsek noise（角度隨機擾動）
- Reflective walls（反射邊界）
- Absorbing walls（吸收邊界）
- 邊界模式切換

**評估**:
- ✅ **應長期保留**（進階物理功能）
- ⚠️ 部分測試依賴統計結果（需多次運行）
- ⚠️ 可能執行較慢

**範例**:
```python
def test_zero_noise_baseline():
    """η=0 時應該沒有 noise 效果"""
    # ✅ 基線測試

def test_reflective_walls_contain_particles():
    """反射邊界應該包含所有粒子"""
    # ✅ 邊界條件測試
```

**⚠️ 潛在問題**:
```python
# 統計測試可能不穩定
def test_noise_reduces_polarization():
    # 需要足夠步數才能觀察統計效果
    for _ in range(1000):  # 可能慢
        system.step(dt=0.05)
```

**保留理由**:
- 進階物理功能的保證
- 邊界模式的正確性

**改善建議**:
- 標記為 `@pytest.mark.slow`
- 考慮縮短步數或使用更明顯的初始條件

---

##### 8. `test_advanced_physics_3d.py` (287 lines) ⭐⭐⭐

**測試內容**:
- 3D Vicsek noise（球面旋轉）
- 3D 邊界模式（PBC/Reflective/Absorbing）
- RNG 可重現性
- 參數傳播

**評估**:
- ✅ **應長期保留**（3D 物理邏輯）
- ⚠️ 與 `test_advanced_physics.py` 有部分重複（2D vs 3D）
- ✅ RNG 可重現性測試很重要

**範例**:
```python
def test_vicsek_noise_rng_reproducibility():
    """相同 seed 應產生相同結果"""
    # ✅ 可重現性測試（critical for science）

def test_eta_parameter_propagation():
    """η 參數應正確傳遞到系統"""
    # ✅ 參數配置正確性
```

**保留理由**:
- 3D 特定邏輯（球面旋轉）
- 可重現性保證（科學計算必須）

**改善建議**:
- 考慮將 2D/3D 共通測試提取為 parametrized test
- 減少重複程式碼

---

### B. 測試品質評估

#### ✅ 優秀的測試特徵

1. **測試行為而非實作**
   ```python
   # ✅ GOOD
   def test_morse_force_repulsion():
       """短距離應產生排斥力（測試結果）"""
       force = compute_morse_force(r=0.1)
       assert force > 0  # 排斥方向
   
   # ❌ BAD (過度耦合)
   def test_morse_force_calls_exp():
       """Morse force 必須呼叫 exp 函數（測試實作）"""
       with mock.patch('math.exp') as mock_exp:
           compute_morse_force(r=0.1)
           assert mock_exp.called  # 測試內部實作
   ```

2. **邊界條件覆蓋**
   - ✅ 零速度、空輸入、極端距離
   - ✅ PBC wrap、牆壁碰撞、資源耗盡
   - ✅ 單一 agent、大量 agent

3. **Regression Tests**
   - ✅ `test_cucker_smale_alignment_bug_fix()`
   - ✅ 已修復的 bug 有對應測試

4. **可重現性**
   - ✅ `test_vicsek_noise_rng_reproducibility()`
   - ✅ 科學計算必須可重現

#### ⚠️ 可改善之處

1. **過度依賴固定迭代次數**
   ```python
   # ⚠️ 可能脆弱
   for _ in range(10):
       system.detect_groups_iteration(...)
   assert system.group_id[0] == expected_group
   
   # ✅ 更好：測試收斂條件
   while not converged(system):
       system.detect_groups_iteration(...)
   assert system.group_id[0] == expected_group
   ```

2. **部分整合測試可能較慢**
   - ⚠️ `test_corridor_navigation()` - 可能需要數百步
   - ⚠️ 統計測試（noise, polarization）- 需要足夠樣本

   **建議**:
   ```python
   @pytest.mark.slow
   def test_corridor_navigation():
       # 標記慢速測試，CI 可選擇性執行
   ```

3. **缺少明確的測試分層**
   - ⚠️ 所有測試混在一個 `tests/` 目錄
   - ✅ 建議結構：
     ```
     tests/
     ├── unit/          # 快速單元測試
     ├── integration/   # 整合測試
     └── e2e/           # 端到端（若有）
     ```

---

### C. 刪除建議

根據規則，以下測試**可考慮刪除或改寫**：

#### 🚫 建議刪除/改寫的測試類型

**目前專案中：幾乎所有測試都應保留！**

經過檢查，本專案的測試品質很高，大部分符合「必須長期保留」的條件：
- ✅ 測試核心 business logic
- ✅ 包含 regression tests
- ✅ 測試邊界條件
- ✅ 測試對外契約（向後相容性）

**唯一可考慮的優化**：

1. **合併重複的 2D/3D 測試**
   ```python
   # 目前：test_advanced_physics.py + test_advanced_physics_3d.py
   # 建議：使用 @pytest.mark.parametrize 合併共通邏輯
   
   @pytest.mark.parametrize("system_class", [Flocking2D, Flocking3D])
   def test_vicsek_noise_reduces_polarization(system_class):
       # 統一測試邏輯，減少維護成本
   ```

2. **移除過度詳細的內部狀態檢查**
   ```python
   # 若存在類似測試（目前未發現明顯案例）：
   # ❌ BAD
   def test_internal_loop_count():
       """檢查 loop 執行 N 次"""
       assert system._loop_counter == expected_count
   
   # ✅ GOOD
   def test_convergence_result():
       """檢查最終收斂結果"""
       assert system.is_converged()
   ```

---

### D. 缺少的測試（建議新增）

#### 🆕 應新增的測試類型

##### 1. **Property-based Tests（Hypothesis）**

適合數值/演算法測試：

```python
from hypothesis import given, strategies as st

@given(
    positions=st.lists(st.floats(min_value=-50, max_value=50), min_size=3, max_size=3),
    box_size=st.floats(min_value=10, max_value=100)
)
def test_pbc_distance_properties(positions, box_size):
    """PBC 距離應滿足：對稱性、三角不等式"""
    p1, p2, p3 = positions
    
    # 對稱性
    assert abs(pbc_dist(p1, p2, box_size) - pbc_dist(p2, p1, box_size)) < 1e-6
    
    # 三角不等式
    d12 = pbc_dist(p1, p2, box_size)
    d23 = pbc_dist(p2, p3, box_size)
    d13 = pbc_dist(p1, p3, box_size)
    assert d13 <= d12 + d23 + 1e-6
```

**好處**：
- 自動生成大量測試案例
- 找到邊界情況（corner cases）
- 驗證數學性質（對稱性、不變量）

---

##### 2. **Smoke Tests（CI 快速驗證）**

```python
@pytest.mark.smoke
def test_import_all_modules():
    """確保所有模組可導入"""
    from flocking_3d import Flocking3D
    from flocking_heterogeneous import HeterogeneousFlocking3D
    from agents.types import AgentType
    from spatial.grid import SpatialGridMixin
    from perception.fov import PerceptionMixin
    # ... 所有公開模組

@pytest.mark.smoke
def test_basic_simulation_runs():
    """最基本模擬可執行（< 1 秒）"""
    system = HeterogeneousFlocking3D(N=10, ...)
    system.initialize(...)
    system.step(dt=0.05)  # 單步測試
    assert system.x[0] is not None
```

**用途**：
- CI 第一階段快速驗證（< 10 秒）
- 確保基本功能未被破壞

---

##### 3. **Benchmark Tests（效能回歸）**

```python
@pytest.mark.benchmark
def test_compute_forces_performance(benchmark):
    """確保物理計算效能不回歸"""
    system = HeterogeneousFlocking3D(N=1000, ...)
    system.initialize(...)
    
    # benchmark 會自動多次執行取平均
    result = benchmark(system.compute_forces)
    
    # 確保不超過基線（例如 10ms）
    assert benchmark.stats['mean'] < 0.01  # 10ms
```

**用途**：
- 防止效能回歸
- 量化優化效果

---

##### 4. **安全性測試（若有對外 API）**

```python
def test_parameter_validation():
    """非法參數應拋出清楚錯誤"""
    with pytest.raises(ValueError, match="beta must be non-negative"):
        FlockingParams(beta=-1.0)
    
    with pytest.raises(ValueError, match="N must be positive"):
        HeterogeneousFlocking3D(N=0, ...)
```

**用途**：
- 防止非法輸入導致 silent error
- 提供清楚錯誤訊息

---

### E. CI/CD 建議

#### 測試執行策略

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  quick-tests:
    # 快速測試（< 1 分鐘）
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ -m "smoke" --maxfail=3
  
  unit-tests:
    # 單元測試（< 5 分鐘）
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ -m "not slow" --cov=src --cov-report=xml
  
  full-suite:
    # 完整測試（< 30 分鐘）
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ --cov=src --cov-report=html
  
  benchmark:
    # 效能測試（週期性執行）
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - run: pytest tests/ -m "benchmark" --benchmark-only
```

---

## 總結建議

### ✅ 必須長期保留（8/8 檔案）

| 檔案 | 優先級 | 原因 |
|------|--------|------|
| `test_physics.py` | ⭐⭐⭐⭐⭐ | 核心物理引擎，含 regression tests |
| `test_perception.py` | ⭐⭐⭐⭐⭐ | Phase 6.1 新功能保護 |
| `test_heterogeneous.py` | ⭐⭐⭐⭐⭐ | 核心異質性邏輯 + 向後相容性 |
| `test_group_detection.py` | ⭐⭐⭐⭐ | 群組偵測演算法正確性 |
| `test_foraging.py` | ⭐⭐⭐⭐ | 覓食系統完整週期 |
| `test_obstacles.py` | ⭐⭐⭐⭐ | SDF 數學正確性 |
| `test_advanced_physics.py` | ⭐⭐⭐ | 進階物理功能（標記為 slow） |
| `test_advanced_physics_3d.py` | ⭐⭐⭐ | 3D 特定邏輯（考慮合併） |

### 🔧 改善建議

1. **測試分層**
   ```
   tests/
   ├── unit/           # 快速單元測試（< 5 秒）
   │   ├── test_physics.py
   │   ├── test_perception.py
   │   └── ...
   ├── integration/    # 整合測試（< 30 秒）
   │   ├── test_foraging.py
   │   ├── test_obstacles.py
   │   └── ...
   └── slow/           # 慢速測試（> 30 秒）
       ├── test_advanced_physics.py
       └── test_advanced_physics_3d.py
   ```

2. **使用 pytest marks**
   ```python
   @pytest.mark.unit
   @pytest.mark.fast
   def test_morse_potential():
       ...
   
   @pytest.mark.integration
   @pytest.mark.slow
   def test_corridor_navigation():
       ...
   ```

3. **合併重複邏輯**
   ```python
   @pytest.mark.parametrize("dimension", ["2d", "3d"])
   def test_vicsek_noise(dimension):
       SystemClass = Flocking2D if dimension == "2d" else Flocking3D
       # 統一測試邏輯
   ```

4. **新增 property-based tests**
   - 使用 Hypothesis 測試數學性質
   - 自動生成邊界案例

5. **新增 smoke tests**
   - CI 第一階段快速驗證
   - 確保基本功能未破壞

---

### 📊 測試覆蓋率目標

| 模組 | 當前估計 | 目標 |
|------|----------|------|
| `flocking_3d.py` | ~85% | 90% |
| `flocking_heterogeneous.py` | ~75% | 85% |
| `perception/fov.py` | 100% | 100% |
| `spatial/grid.py` | ~70% | 85% |
| `behaviors/*` | ~80% | 90% |

---

### 🚀 行動計畫

#### 短期（1-2 週）

1. ✅ 新增 pytest marks (`@pytest.mark.unit`, `@pytest.mark.slow`)
2. ✅ 重組測試目錄結構（unit/integration/slow）
3. ✅ 新增 smoke tests（< 10 秒快速驗證）

#### 中期（1-2 月）

4. ✅ 合併 2D/3D 重複測試（使用 parametrize）
5. ✅ 新增 property-based tests（Hypothesis）
6. ✅ 新增 benchmark tests（效能回歸保護）

#### 長期（持續）

7. ✅ 維持測試覆蓋率 > 85%
8. ✅ 每個 bug fix 必須附帶 regression test
9. ✅ 每個新功能必須附帶單元測試

---

## 結論

### ✅ 專案測試品質評估：**優秀**

- ✅ 核心邏輯有完整單元測試
- ✅ 已修復的 bug 有 regression tests
- ✅ 邊界條件覆蓋良好
- ✅ 向後相容性有保護
- ✅ 測試大多測「行為」而非「實作」

### ⚠️ 改善空間

- ⚠️ 缺少明確測試分層（unit/integration/slow）
- ⚠️ 部分測試可能較慢（應標記為 `@pytest.mark.slow`）
- ⚠️ 缺少 property-based tests（Hypothesis）
- ⚠️ 缺少 smoke tests（CI 快速驗證）

### 🎯 核心原則

**根據「回歸風險高嗎？」判準**：

| 測試檔案 | 回歸風險 | 決策 |
|---------|---------|------|
| `test_physics.py` | ⚠️ 極高 | ✅ 永久保留 |
| `test_perception.py` | ⚠️ 高 | ✅ 永久保留 |
| `test_heterogeneous.py` | ⚠️ 極高 | ✅ 永久保留 |
| `test_group_detection.py` | ⚠️ 高 | ✅ 永久保留 |
| `test_foraging.py` | ⚠️ 中 | ✅ 永久保留 |
| `test_obstacles.py` | ⚠️ 中 | ✅ 永久保留 |
| `test_advanced_physics.py` | ⚠️ 中 | ✅ 保留（標記 slow） |
| `test_advanced_physics_3d.py` | ⚠️ 中 | ✅ 保留（考慮合併） |

---

**評估結論**: 
- **可刪除的測試：0 個**
- **應長期保留：8 個**
- **建議改善：測試分層、標記、新增 property-based tests**

---

**報告生成日期**: 2026-02-07  
**下次審查建議**: Phase 6 完成後（~2 週後）
