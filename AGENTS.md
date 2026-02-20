# AGENTS.md - Developer Guide

**Target**: Python engineers, researchers, contributors

This doc describes the project from an **engineering perspective**: goals, architecture, and skills needed to contribute.

---

## Philosophy

### Core Principles (Vibe Engineering)

**1. Good Taste > Clever Code**
- Eliminate unnecessary conditionals
- Let data structures do the work
- Code should read like physics equations

**2. Never Break Userspace**
- Absolute API compatibility
- Test before refactoring
- Deprecate, don't delete

**3. Pragmatism > Theory**
- Solve real problems
- Ship working code
- Optimize later

**4. Simplicity = Safety**
- Complexity is risk
- Short functions (<50 lines)
- Single responsibility

**5. Observability First**
- Can you debug it at 3 AM?
- Logs tell a story
- State is traceable

**6. Structural Performance Constraints**
- Max 3 nested loops (or explain why)
- O(N²) → O(N) before scaling
- Profiling beats intuition

---

## Project Structure

```
alife/
├── README.md                          # Quick start guide
├── AGENTS.md                          # You are here
│
├── src/                               # Core implementation
│   ├── agents/
│   │   └── types.py                   # Agent type definitions (54L)
│   ├── behaviors/
│   │   ├── foraging.py                # Energy & resource system (380L)
│   │   ├── predation.py               # Attack & death mechanics (262L)
│   │   └── reproduction.py            # Evolution system (227L, WIP)
│   ├── spatial/
│   │   ├── grid.py                    # O(N) spatial acceleration (206L)
│   │   └── group_detection.py         # Label propagation clustering (291L)
│   ├── perception/
│   │   └── fov.py                     # Field of view filtering (128L)
│   ├── navigation/
│   │   └── goal_seeking.py            # Goal-directed movement (224L)
│   ├── flocking_2d.py                 # 2D physics engine (~500L)
│   ├── flocking_3d.py                 # 3D physics engine (~500L)
│   ├── flocking_heterogeneous.py      # Main coordinator (753L)
│   ├── resources.py                   # Resource system (246L)
│   └── obstacles.py                   # SDF-based collision (~220L)
│
├── tests/                             # Unit tests (89 tests)
│   ├── test_physics.py                # Base physics tests (13)
│   ├── test_advanced_physics*.py      # 2D/3D advanced physics (19)
│   ├── test_heterogeneous.py          # Agent types tests (12)
│   ├── test_foraging.py               # Foraging tests (9)
│   ├── test_perception.py             # FOV tests (7)
│   ├── test_navigation.py             # Goal-seeking tests (13)
│   ├── integration/                   # Integration tests
│   │   ├── test_improvements.py       # Core improvements
│   │   ├── test_death_removal.py      # Death mechanics
│   │   └── test_resource_competition.py
│   └── grid/                          # Grid optimization experiments (13 files)
│
├── experiments/                       # Runnable demos
│   ├── demo_2d.py                     # 2D quick demo
│   ├── demo_3d.py                     # 3D quick demo
│   ├── demo_foraging.py               # Foraging demo (3 scenarios)
│   ├── demo_heterogeneous.py          # Agent types demo
│   └── benchmark_optimized.py         # Performance benchmark
│
├── backend/                           # WebSocket server (production ready)
│   ├── server.py                      # WebSocket server (30 FPS)
│   ├── simulation_manager.py          # State management
│   └── serializer.py                  # Binary protocol
│
├── frontend/                          # React + WebGPU (WIP)
│   ├── src/
│   │   ├── components/
│   │   ├── renderer/                  # WebGPU renderer
│   │   └── store/                     # Zustand state
│   └── public/
│
├── docs/                              # Documentation
│   ├── GUIDE.md                       # User guide
│   ├── API.md                         # API reference (18KB)
│   ├── CHANGELOG.md                   # Version history (29KB)
│   ├── REFACTORING_REPORT.md          # Phase 5 report
│   ├── WEBGPU_INTEGRATION_PLAN.md     # Frontend architecture
│   ├── archive/                       # Historical docs (sessions, debug logs)
│   ├── reports/                       # Performance & optimization reports
│   └── status/                        # Project status snapshots
│
└── Tools (Root level)
    ├── analyze_energy_balance.py      # Energy balance calculator
    ├── benchmark_performance.py       # Performance profiler
    └── plot_performance.py            # Visualization tool
```

---

## Architecture

### Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| **Compute** | Taichi (Python) | C/CUDA perf, Python syntax |
| **Science** | NumPy | Mature ecosystem |
| **Backend** | WebSocket (asyncio) | <33ms latency |
| **Frontend** | React + WebGPU | Modern, GPU-accelerated |
| **Test** | pytest | Standard, plugin-rich |

### System Flow

```
Frontend (React + WebGPU)
    │
    ├── WebGPU Renderer      → GPU particle system
    ├── Zustand Store        → State management
    └── Control Panel        → Parameter UI
    │
    └─[WebSocket ws://localhost:8765]─┐
                                       │
Backend (Python asyncio)              │
    │                                 │
    ├── WebSocket Server (30 FPS)    │
    ├── Simulation Manager           │
    └── Binary Serializer            │
    │                                │
    └──[Taichi GPU Engine]───────────┘
         │
         ├── HeterogeneousFlocking3D (753L)
         │   ├── Agents (types, behaviors)
         │   ├── Spatial (grid, groups)
         │   └── Behaviors (foraging, predation)
         │
         ├── Resources (consumable, renewable)
         └── Obstacles (SDF collision)
```

---

## Mixin Architecture

### Why Mixin?

**Taichi Constraints**:
- All `ti.fields` must be defined in `__init__`
- Deep inheritance causes field duplication
- No `hasattr()` in kernels

**Solution**:
- Use **Mixin Pattern** for composition
- Each mixin = one independent feature
- Main class orchestrates via multiple inheritance

### Architecture Diagram

```python
class HeterogeneousFlocking3D(
    Flocking3D,              # Base physics (Velocity Verlet)
    SpatialGridMixin,        # O(N) neighbor search
    GroupDetectionMixin,     # Label propagation
    ForagingBehaviorMixin,   # Energy & resources
    PredationBehaviorMixin,  # Attack & death
    PerceptionMixin,         # FOV filtering
    NavigationMixin,         # Goal-seeking
):
    """Main coordinator: combines all modules"""
```

### Initialization Flow

```python
def __init__(self, N, params, agent_types, ...):
    # 1. Base physics
    super().__init__(N, params)
    
    # 2. Init mixins (order matters: dependencies)
    self.init_spatial_grid(N, box_size, cell_size)
    self.init_group_detection(N, max_groups)
    self.init_foraging(N, resources, energy_threshold)
    self.init_predation(N, attack_radius)
    self.init_perception(fov_angle)
    self.init_navigation(goal_strength)
    
    # 3. Agent type system
    self._init_agent_types(agent_types)
```

### Main Loop Design

```python
def step(self, dt: float):
    """
    Single simulation step
    
    Phases:
    1. Spatial indexing
    2. Target search (resources, prey)
    3. Physics (Velocity Verlet)
    4. Ecological interactions
    5. Resource regeneration
    6. Periodic group detection
    """
    # Phase 1: Spatial indexing
    self.assign_agents_to_grid()
    
    # Phase 2: Target search
    self.find_nearest_resources()  # ForagingBehaviorMixin
    self.find_nearest_prey()       # PredationBehaviorMixin
    
    # Phase 3: Physics integration
    self.compute_forces()          # Base physics
    self.verlet_step1(dt)
    self.compute_forces()
    self.verlet_step2(dt)
    
    # Phase 4: Ecological interactions
    self.consume_resources_step()  # Foraging
    self.attack_prey_step()        # Predation
    self.resources.regenerate_step()
    
    # Phase 5: Periodic group detection (every 10 steps)
    self.step_counter += 1
    if self.step_counter >= self.group_detection_interval:
        self.update_groups()
        self.step_counter = 0
```

---

## Module Responsibilities

| Module | Responsibility | Lines | Status |
|--------|---------------|-------|--------|
| **agents/types.py** | Agent type definitions & behavior params | 54 | ✅ |
| **spatial/grid.py** | O(N) spatial acceleration (cell list) | 206 | ✅ |
| **spatial/group_detection.py** | Label propagation clustering | 291 | ✅ |
| **behaviors/foraging.py** | Energy, resources, health states | 380 | ✅ |
| **behaviors/predation.py** | Attack, death, dynamic success rate | 262 | ✅ |
| **behaviors/reproduction.py** | Evolution system (trait inheritance) | 227 | 🚧 |
| **perception/fov.py** | Field of view filtering | 128 | ✅ |
| **navigation/goal_seeking.py** | Goal-directed movement (PBC-aware) | 224 | ✅ |
| **flocking_3d.py** | Base physics (Morse, Rayleigh, Alignment) | ~500 | ✅ |
| **flocking_heterogeneous.py** | Main coordinator (integrates all) | 753 | ✅ |
| **resources.py** | Consumable & renewable resources | 246 | ✅ |
| **obstacles.py** | SDF-based collision detection | ~220 | ✅ |

---

## Required Skills

### 1. Python ⭐⭐⭐⭐⭐

**Must Know**:
- OOP (classes, inheritance, mixins)
- Type hints (`dataclass`, `List`, `Optional`)
- NumPy (arrays, vectorization)
- Asyncio (for WebSocket backend)

**Resources**:
- [Python Tutorial](https://docs.python.org/3/tutorial/)
- [NumPy User Guide](https://numpy.org/doc/stable/user/)

---

### 2. Taichi ⭐⭐⭐⭐

**Must Know**:
- `@ti.data_oriented` decorator
- `@ti.kernel` vs `@ti.func`
- `ti.field()`, `ti.Vector.field()`
- Auto-parallelization: `for i in self.x`
- Constraints: no Python stdlib, no dynamic types

**Example**:
```python
@ti.data_oriented
class MySystem:
    def __init__(self, N):
        self.x = ti.Vector.field(3, dtype=ti.f32, shape=N)
        self.v = ti.Vector.field(3, dtype=ti.f32, shape=N)
    
    @ti.kernel
    def update(self):
        """Runs on GPU, auto-parallelized"""
        for i in self.x:  # Parallel loop
            self.v[i] += ti.math.vec3(0, -9.8, 0) * 0.01
            self.x[i] += self.v[i] * 0.01
```

**Resources**:
- [Taichi Docs](https://docs.taichi-lang.org/)
- [Taichi Examples](https://github.com/taichi-dev/taichi/tree/master/python/taichi/examples)

---

### 3. Physics Simulation ⭐⭐⭐

**Must Know**:
- Newton's laws
- Numerical integration (Euler, Velocity Verlet)
- Periodic boundary conditions (PBC)

**Core Formulas**:

**Morse Potential** (repulsion + attraction):
```
F_morse = Cr * exp(-r/lr) - Ca * exp(-r/la)
```

**Cucker-Smale Alignment**:
```
F_align = (β/N) * Σ_j (v_j - v_i) / (1 + r_ij²)
```

**Velocity Verlet**:
```
v_half = v + 0.5 * F/m * dt
x_new = x + v_half * dt
v_new = v_half + 0.5 * F_new/m * dt
```

**Resources**:
- [ETH Zurich - Physics Simulation](https://cgl.ethz.ch/teaching/simulation/)

---

### 4. Spatial Data Structures ⭐⭐⭐

**Spatial Grid (Cell List)**: O(N²) → O(N)

```python
# Divide space into cubic cells
cell_size = 2 * r_cutoff
grid_nx = ceil(box_size / cell_size)

# Assign agents to cells
cell_id = floor(x_i / cell_size)

# Search only 27 neighboring cells (3x3x3)
for neighbor_cell in adjacent_27_cells(cell_id):
    for j in agents_in_cell(neighbor_cell):
        if distance(i, j) < r_cutoff:
            compute_force(i, j)
```

---

### 5. Testing (TDD) ⭐⭐⭐

**Test Pyramid**:
```
       ┌───────────┐
       │ E2E Tests │  Few (integration)
       ├───────────┤
       │Integration│  Some (module interactions)
       ├───────────┤
       │Unit Tests │  Many (single functions)
       └───────────┘
```

**Run Tests**:
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_physics.py -v

# Coverage
pytest --cov=src tests/
```

---

## Development Workflow

### 1. Setup

```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repo
git clone <repo-url>
cd alife

# Install dependencies
uv pip install taichi numpy matplotlib pytest

# Verify installation
uv run python -c "import taichi as ti; ti.init(arch=ti.cpu); print('OK')"
```

---

### 2. Add New Feature (Example: New Mixin)

#### Step 1: Plan
- Define module responsibility (single responsibility principle)
- Identify dependencies
- Design API (public methods, parameters)

#### Step 2: Implement

```python
# src/new_module/feature.py
import taichi as ti

@ti.data_oriented
class NewFeatureMixin:
    """New feature module"""
    
    def init_new_feature(self, N: int, param1: float):
        self.feature_field = ti.field(dtype=ti.f32, shape=N)
        self.param1 = param1
    
    @ti.kernel
    def compute_new_feature(self):
        for i in self.feature_field:
            self.feature_field[i] = ti.sin(self.x[i].x) * self.param1
```

#### Step 3: Integrate

```python
# src/flocking_heterogeneous.py
from new_module.feature import NewFeatureMixin

class HeterogeneousFlocking3D(
    ...,
    NewFeatureMixin,
):
    def __init__(self, ...):
        super().__init__(...)
        self.init_new_feature(N, param1=1.0)
    
    def step(self, dt):
        # ... existing logic
        self.compute_new_feature()
```

#### Step 4: Test

```python
# tests/test_new_feature.py
def test_feature_initialization():
    system = TestSystem(N=10)
    assert system.param1 == 1.0

def test_feature_computation():
    system = TestSystem(N=10)
    system.compute_new_feature()
    # Verify results...
```

#### Step 5: Commit

```bash
# Ensure tests pass
pytest tests/ -v

# Commit
git add src/new_module/ tests/test_new_feature.py
git commit -m "feat: add new feature mixin

- Implement NewFeatureMixin
- Add 5 unit tests
- Update API docs"

git push origin feature/new-module
```

---

## Common Tasks

### Task 1: Add Agent Type

**File**: `src/agents/types.py`

```python
# 1. Add enum
class AgentType(IntEnum):
    NEW_TYPE = 4

# 2. Define behavior
DEFAULT_PROFILES[AgentType.NEW_TYPE] = AgentTypeProfile(
    beta=1.2,
    eta=0.15,
    v0=1.1,
    color=(0.5, 0.5, 0.5)  # Gray
)
```

---

### Task 2: Performance Optimization

**Workflow**:

1. **Profile**:
```python
import cProfile
profiler = cProfile.Profile()
profiler.enable()
system.run(steps=1000, dt=0.05)
profiler.disable()
profiler.print_stats(sort='cumtime')
```

2. **Identify Bottlenecks** (common issues):
   - ❌ Too many Python-Taichi boundary crossings
   - ❌ No spatial acceleration (O(N²) search)
   - ❌ Frequent GPU-CPU transfers

3. **Optimize**:
   - ✅ Merge `@ti.kernel` calls
   - ✅ Use spatial grid
   - ✅ Reduce `to_numpy()` calls

---

### Task 3: Debug Taichi Kernel

**Technique 1: Print Debug**
```python
@ti.kernel
def debug_kernel(self):
    for i in self.x:
        if i == 0:
            print(f"Agent 0: pos={self.x[i]}, vel={self.v[i]}")
```

**Technique 2: Visualize**
```python
positions = system.x.to_numpy()

import matplotlib.pyplot as plt
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2])
plt.show()
```

**Technique 3: Isolate**
```bash
# Run single test
pytest tests/test_spatial_grid.py::test_neighbor_search -v

# Debug with pdb
pytest tests/test_spatial_grid.py::test_neighbor_search --pdb
```

---

## FAQ

### Q1: Taichi Type Error

**Problem**: `TypeError: expected ti.f32, got float`

**Solution**:
```python
# ❌ Wrong
self.field[i] = 1.0

# ✅ Correct
self.field[i] = ti.f32(1.0)
```

---

### Q2: Mixin Field Not Found

**Problem**: LSP error `Attribute 'agent_energy' does not exist`

**Explanation**:
- This is **expected behavior** (not a bug)
- Mixin fields are created at runtime
- LSP can't statically analyze Taichi fields

**Solution**:
- Ignore warning (doesn't affect execution)
- Or use `# type: ignore`

---

### Q3: Slow Performance

**Checklist**:
1. ✅ Using GPU? `ti.init(arch=ti.gpu)`
2. ✅ Avoid frequent GPU-CPU transfers? (reduce `to_numpy()`)
3. ✅ Using spatial acceleration? (`SpatialGridMixin`)
4. ✅ Avoiding deep nested loops? (<3 levels)

**Benchmark**:
```bash
uv run python benchmark_performance.py
```

---

## References

### Official Docs
- [Taichi](https://docs.taichi-lang.org/)
- [NumPy](https://numpy.org/doc/stable/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

### Project Docs
- [README.md](README.md) - Quick start
- [docs/API.md](docs/API.md) - API reference
- [docs/GUIDE.md](docs/GUIDE.md) - User guide
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - Version history

### Papers
- Vicsek et al., "Novel type of phase transition in self-driven particles" (PRL 1995)
- Cucker & Smale, "Emergent Behavior in Flocks" (TAM 2007)
- Reynolds, "Flocks, herds and schools" (SIGGRAPH 1987)

---

## Contribution Guidelines

### Pull Request Process

1. **Fork** → Create branch → Implement feature
2. **Test**: Coverage > 80%
3. **CI**: All tests must pass
4. **Docs**: Update API docs
5. **Review**: Respond to reviewer comments

### Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Example**:
```
feat(perception): add FOV filtering mixin

- Implement PerceptionMixin with is_in_fov()
- Integrate with compute_forces()
- Add 7 unit tests (100% coverage)

Closes #42
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Tests
- `perf`: Performance optimization

---

## Roadmap

### Phase 5 ✅ (2026-02-07)
- ✅ Modular refactoring (-34% main file size)
- ✅ 6 independent modules
- ✅ Complete tests & docs

### Phase 6 ✅ (2026-02-08)
- ✅ PerceptionMixin (FOV filtering)
- ✅ NavigationMixin (Goal-seeking)
- ✅ -7.5% code reduction (814 → 753 lines)

### Phase 7 ✅ (2026-02-08)
- ✅ Mass dynamics correction (F=ma)
- ✅ Soft-sphere repulsion
- ✅ Health/weakness system
- ✅ Dynamic attack success rate
- ✅ Death & removal mechanics
- ✅ Resource competition (FIFO)

### Phase 8 🚀 (Current)
- 🔄 File organization (tests, docs)
- ⏳ Reproduction system integration
- ⏳ WebGPU frontend completion

### Future 💡
- Parameter auto-tuning (Bayesian optimization)
- More agent types (Scavenger, Guardian)
- 3D obstacle visualization
- Distributed simulation (multi-GPU)

---

**Last Updated**: 2026-02-08  
**Maintainer**: Project Team  
**Issues**: GitHub Issues
