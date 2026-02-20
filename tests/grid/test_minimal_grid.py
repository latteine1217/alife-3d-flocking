import sys
sys.path.insert(0, "src")
import time
import taichi as ti
import numpy as np

ti.init(arch=ti.metal)

# 創建最小測試
N = 10
max_agents_per_cell = 32
grid_res = 11
n_cells = grid_res ** 3

# Fields
x = ti.Vector.field(3, ti.f32, N)
f = ti.Vector.field(3, ti.f32, N)
cell_count = ti.field(ti.i32, n_cells)
cell_agents = ti.field(ti.i32, (n_cells, max_agents_per_cell))
agent_cell_id = ti.field(ti.i32, N)

# 初始化
x.from_numpy(np.random.rand(N, 3).astype(np.float32) * 10)
agent_cell_id.fill(0)
cell_count.fill(1)
cell_agents.fill(0)

@ti.kernel
def test_grid_loop():
    """最小化的 Grid 迴圈測試"""
    for i in x:
        cell_id = agent_cell_id[i]
        res = grid_res
        
        # 解析 cell
        iz = cell_id // (res * res)
        remainder = cell_id % (res * res)
        iy = remainder // res
        ix = remainder % res
        
        force = ti.Vector([0.0, 0.0, 0.0])
        
        # 27 個鄰近 cells
        for dz in ti.static(range(-1, 2)):
            for dy in ti.static(range(-1, 2)):
                for dx in ti.static(range(-1, 2)):
                    nx = ix + dx
                    ny = iy + dy
                    nz = iz + dz
                    
                    if 0 <= nx < res and 0 <= ny < res and 0 <= nz < res:
                        neighbor_cell = nx + ny*res + nz*res*res
                        n_agents_in_cell = cell_count[neighbor_cell]
                        
                        # 問題可能在這裡
                        for local_idx in range(max_agents_per_cell):
                            if local_idx >= n_agents_in_cell:
                                break
                            
                            j = cell_agents[neighbor_cell, local_idx]
                            force += x[j]  # 簡單計算
        
        f[i] = force

print("編譯 kernel...")
start = time.time()
test_grid_loop()  # 第一次調用會觸發編譯
compile_time = time.time() - start
print(f"編譯時間: {compile_time:.2f} 秒")

print("執行 kernel (warmup 後)...")
start = time.time()
test_grid_loop()
exec_time = (time.time() - start) * 1000
print(f"執行時間: {exec_time:.2f} ms")

print(f"\n✅ 測試完成")
print(f"結果範例: f[0] = {f[0]}")
