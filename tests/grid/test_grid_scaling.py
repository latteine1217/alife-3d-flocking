import sys
sys.path.insert(0, "src")
import time
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal)

def create_simple_grid_kernel(system):
    @ti.kernel
    def compute_forces_simple_grid():
        for i in system.f:
            system.f[i] = ti.Vector([0.0, 0.0, 0.0])
        
        Ca, Cr = system.p[0], system.p[1]
        la, lr = system.p[2], system.p[3]
        rc, rc2 = system.p[4], system.p[4] * system.p[4]
        inv_la, inv_lr = 1.0 / la, 1.0 / lr
        
        for i in system.x:
            if system.agent_alive[i] == 0:
                continue
            
            xi = system.x[i]
            force = ti.Vector([0.0, 0.0, 0.0])
            cell_id = system.agent_cell_id[i]
            
            if cell_id >= 0:
                res = system.grid_resolution
                iz = cell_id // (res * res)
                remainder = cell_id % (res * res)
                iy, ix = remainder // res, remainder % res
                
                for cell_offset in ti.static(range(27)):
                    dz, dy, dx = (cell_offset // 9) - 1, ((cell_offset % 9) // 3) - 1, (cell_offset % 3) - 1
                    nx, ny, nz = ix + dx, iy + dy, iz + dz
                    
                    if 0 <= nx < res and 0 <= ny < res and 0 <= nz < res:
                        neighbor_cell = nx + ny*res + nz*res*res
                        max_check = ti.min(system.cell_count[neighbor_cell], 8)
                        
                        for local_idx in range(max_check):
                            j = system.cell_agents[neighbor_cell, local_idx]
                            if i != j and system.agent_alive[j] == 1:
                                rij = system.pbc_dist(xi, system.x[j])
                                r2 = rij.dot(rij)
                                
                                if 1e-6 < r2 < rc2:
                                    r = ti.sqrt(r2)
                                    exp_a, exp_r = ti.exp(-r * inv_la), ti.exp(-r * inv_lr)
                                    force += (Ca * inv_la * exp_a - Cr * inv_lr * exp_r) * rij / r
            
            system.f[i] = force
    return compute_forces_simple_grid

def test_N(N):
    print(f"\n{'='*60}")
    print(f"N = {N}")
    print(f"{'='*60}")
    
    system = HeterogeneousFlocking3D(
        N=N, params=FlockingParams(),
        agent_types=[AgentType.FOLLOWER]*N,
        enable_fov=False, max_agents=max(200, N)
    )
    system.initialize(box_size=10.0, seed=42)
    system.assign_agents_to_grid()
    
    grid_kernel = create_simple_grid_kernel(system)
    
    # Warmup
    system.compute_forces()
    grid_kernel()
    
    # Benchmark原始版本
    times_orig = []
    for _ in range(5):
        start = time.time()
        system.compute_forces()
        times_orig.append((time.time() - start) * 1000)
    orig_avg = sum(times_orig) / len(times_orig)
    
    # Benchmark Grid版本
    times_grid = []
    for _ in range(5):
        start = time.time()
        grid_kernel()
        times_grid.append((time.time() - start) * 1000)
    grid_avg = sum(times_grid) / len(times_grid)
    
    speedup = orig_avg / grid_avg
    
    print(f"原始版本: {orig_avg:.3f} ms")
    print(f"Grid版本:  {grid_avg:.3f} ms")
    print(f"加速比:   {speedup:.2f}x {'✅' if speedup > 1 else '❌'}")
    
    return orig_avg, grid_avg, speedup

# 測試不同 N
results = []
for N in [10, 30, 50, 100]:
    try:
        results.append((N, *test_N(N)))
    except Exception as e:
        print(f"❌ N={N} 失敗: {e}")
        break

print(f"\n{'='*60}")
print("總結")
print(f"{'='*60}")
print(f"{'N':<6} {'原始(ms)':<12} {'Grid(ms)':<12} {'加速比':<8}")
print("-" * 60)
for N, orig, grid, speedup in results:
    status = "✅" if speedup > 1 else "❌"
    print(f"{N:<6} {orig:<12.3f} {grid:<12.3f} {speedup:<8.2f} {status}")
