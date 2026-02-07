#!/usr/bin/env python3
"""
2D Flocking 快速展示

用法：
  python demo_2d.py                 # 標準配置
  python demo_2d.py --demo 2        # 高對齊配置
  python demo_2d.py --help          # 查看所有選項
"""

import sys
import argparse

sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
sys.path.insert(0, "/Users/latteine/Documents/coding/alife/experiments")

from flocking_2d import Flocking2D, FlockingParams
from visualizer_2d import Visualizer2D


def main():
    parser = argparse.ArgumentParser(
        description="快速啟動 2D Flocking 可視化展示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Demo 選項：
  1  標準配置（推薦）
  2  高對齊配置
  3  混亂配置（無對齊）
  4  大規模（N=500）
  5  強吸引配置

範例：
  python demo_2d.py                 # 預設（標準配置）
  python demo_2d.py --demo 2        # 高對齊
  python demo_2d.py --N 500         # 自訂粒子數
        """,
    )

    parser.add_argument(
        "--demo",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=1,
        help="選擇預設配置（預設: 1）",
    )

    parser.add_argument("--N", type=int, help="粒子數量（覆蓋 demo 預設）")
    parser.add_argument("--beta", type=float, help="對齊力強度（覆蓋 demo 預設）")
    parser.add_argument("--alpha", type=float, help="Rayleigh 係數（覆蓋 demo 預設）")
    parser.add_argument("--box-size", type=float, help="Box 大小（覆蓋 demo 預設）")

    args = parser.parse_args()

    # Demo 配置
    configs = {
        1: {"N": 300, "beta": 1.0, "alpha": 2.0, "box_size": 50.0, "name": "標準配置"},
        2: {
            "N": 300,
            "beta": 2.5,
            "alpha": 1.5,
            "box_size": 50.0,
            "name": "高對齊配置",
        },
        3: {
            "N": 300,
            "beta": 0.0,
            "alpha": 3.0,
            "box_size": 50.0,
            "name": "混亂配置（無對齊）",
        },
        4: {
            "N": 500,
            "beta": 1.5,
            "alpha": 2.0,
            "box_size": 70.0,
            "name": "大規模配置",
        },
        5: {
            "N": 300,
            "beta": 1.5,
            "alpha": 1.0,
            "box_size": 50.0,
            "name": "強吸引配置",
            "Ca": 3.0,
            "la": 5.0,
            "rc": 20.0,
        },
    }

    config = configs[args.demo]

    # 應用命令列覆蓋
    if args.N:
        config["N"] = args.N
    if args.beta is not None:
        config["beta"] = args.beta
    if args.alpha is not None:
        config["alpha"] = args.alpha
    if args.box_size:
        config["box_size"] = args.box_size

    print("\n" + "=" * 70)
    print(f"  啟動 2D Demo {args.demo}: {config['name']}")
    print("=" * 70)

    # 建立參數（2D 版本不需要 dim 參數）
    params_dict = {
        "Ca": config.get("Ca", 1.5),
        "Cr": 2.0,
        "la": config.get("la", 2.5),
        "lr": 0.5,
        "rc": config.get("rc", 15.0),
        "alpha": config["alpha"],
        "v0": 1.0,
        "beta": config["beta"],
        "box_size": config["box_size"],
        "use_pbc": True,
    }

    params = FlockingParams(**params_dict)

    # 建立 2D 系統
    system = Flocking2D(N=config["N"], params=params)
    system.initialize(box_size=config["box_size"] * 0.1, seed=42)

    print(
        f"\n✅ 2D 系統已初始化：N={config['N']}, beta={config['beta']}, alpha={config['alpha']}"
    )

    # 建立 2D 可視化器
    viz = Visualizer2D(
        system=system,
        window_size=(1200, 1000),
        show_velocity=True,
        show_box=True,
    )

    # 執行
    viz.run(steps=0, dt=0.01)


if __name__ == "__main__":
    main()
