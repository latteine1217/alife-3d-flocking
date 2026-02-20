import sys
sys.path.insert(0, "src")
import time
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal)

N = 5
system = HeterogeneousFlocking3D(
    N=N, params=FlockingParams(), 
    agent_types=[AgentType.FOLLOWER]*N,
    enable_fov=False, max_agents=200
)
system.initialize(box_size=10.0, seed=42)
system.assign_agents_to_grid()

print("測試 1: 原始 compute_forces()")
start = time.time()
system.compute_forces()
t1 = (time.time() - start) * 1000
print(f"  編譯 + 執行: {t1:.2f} ms")

start = time.time()
system.compute_forces()
t2 = (time.time() - start) * 1000
print(f"  第 2 次執行: {t2:.2f} ms\n")

print("測試 2: compute_forces_grid() 編譯...")
print("  (如果超過 10 秒還沒反應，說明卡在編譯)")
start_compile = time.time()

# 嘗試調用，設置 timeout
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("編譯超時")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(15)  # 15 秒 timeout

try:
    system.compute_forces_grid()
    compile_time = time.time() - start_compile
    signal.alarm(0)  # 取消 alarm
    
    print(f"  ✅ 編譯成功: {compile_time:.2f} 秒")
    
    start = time.time()
    system.compute_forces_grid()
    t3 = (time.time() - start) * 1000
    print(f"  第 2 次執行: {t3:.2f} ms")
    
    print(f"\n對比:")
    print(f"  原始: {t2:.2f} ms")
    print(f"  Grid: {t3:.2f} ms")
    print(f"  比例: {t3/t2:.2f}x")
    
except TimeoutError:
    print(f"  ❌ 編譯超時 (>15 秒)")
    print("  結論: Kernel 太複雜，Taichi 編譯器無法處理")
