#!/usr/bin/env python3
"""
2D vs 3D Flocking 對比展示（多程序版本）

由於 Taichi 限制，使用多程序分別執行 2D 和 3D 模擬
"""

import sys
import subprocess
import json
import argparse


def run_simulation(dim: int, N: int, steps: int):
    """在子程序中執行模擬"""
    if dim == 2:
        script = f"""
import sys
sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
from flocking_2d import Flocking2D, FlockingParams

params = FlockingParams(beta=1.0, alpha=2.0)
system = Flocking2D(N={N}, params=params)
system.initialize(box_size=5.0, seed=42)

results = {{"Rg": [], "P": [], "v": []}}

for step in range({steps}):
    system.step(0.01)
    if step % 10 == 0:
        diag = system.compute_diagnostics()
        results["Rg"].append(diag["Rg"])
        results["P"].append(diag["polarization"])
        results["v"].append(diag["mean_speed"])

import json
print(json.dumps(results))
"""
    else:  # dim == 3
        script = f"""
import sys
sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
from flocking_3d import Flocking3D, FlockingParams

params = FlockingParams(beta=1.0, alpha=2.0)
system = Flocking3D(N={N}, params=params)
system.initialize(box_size=5.0, seed=42)

results = {{"Rg": [], "P": [], "v": []}}

for step in range({steps}):
    system.step(0.01)
    if step % 10 == 0:
        diag = system.compute_diagnostics()
        results["Rg"].append(diag["Rg"])
        results["P"].append(diag["polarization"])
        results["v"].append(diag["mean_speed"])

import json
print(json.dumps(results))
"""

    result = subprocess.run(
        ["uv", "run", "python", "-c", script], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ {dim}D 模擬失敗:")
        print(result.stderr)
        return None

    return json.loads(result.stdout.strip().split("\n")[-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--N", type=int, default=100)
    parser.add_argument("--steps", type=int, default=100)
    args = parser.parse_args()

    print("=" * 70)
    print("2D vs 3D Flocking Dynamics Comparison")
    print("=" * 70)
    print(f"\n配置: N={args.N}, steps={args.steps}\n")

    print("執行 2D 模擬...")
    data_2d = run_simulation(2, args.N, args.steps)

    print("執行 3D 模擬...")
    data_3d = run_simulation(3, args.N, args.steps)

    if not data_2d or not data_3d:
        return

    print("\n" + "=" * 70)
    print("最終統計")
    print("=" * 70)

    import numpy as np

    print(f"\n2D 系統:")
    print(
        f"  Rg:              {np.mean(data_2d['Rg']):.3f} ± {np.std(data_2d['Rg']):.3f}"
    )
    print(
        f"  Polarization:    {np.mean(data_2d['P']):.4f} ± {np.std(data_2d['P']):.4f}"
    )
    print(
        f"  Mean Speed:      {np.mean(data_2d['v']):.4f} ± {np.std(data_2d['v']):.4f}"
    )

    print(f"\n3D 系統:")
    print(
        f"  Rg:              {np.mean(data_3d['Rg']):.3f} ± {np.std(data_3d['Rg']):.3f}"
    )
    print(
        f"  Polarization:    {np.mean(data_3d['P']):.4f} ± {np.std(data_3d['P']):.4f}"
    )
    print(
        f"  Mean Speed:      {np.mean(data_3d['v']):.4f} ± {np.std(data_3d['v']):.4f}"
    )

    print("\n✅ 比較完成")


if __name__ == "__main__":
    main()
