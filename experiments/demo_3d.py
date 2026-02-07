#!/usr/bin/env python3
"""
快速啟動視覺化展示

用法：
  python quickstart_viz.py              # 標準配置
  python quickstart_viz.py --demo 2      # 高對齊配置
  python quickstart_viz.py --help        # 查看所有選項
"""

import sys
import argparse

sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
sys.path.insert(0, "/Users/latteine/Documents/coding/alife/experiments")

from flocking_3d import OptimizedFlockingV2, FlockingParams

# 載入視覺化器
exec(open("/Users/latteine/Documents/coding/alife/experiments/visualizer_3d.py").read())


def main():
    parser = argparse.ArgumentParser(
        description="快速啟動 V2 視覺化展示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Demo 選項：
  1  標準配置（推薦）
  2  高對齊配置
  3  混亂配置
  4  大規模（N=500）
  5  強吸引配置

範例：
  python quickstart_viz.py              # 預設（標準配置）
  python quickstart_viz.py --demo 2      # 高對齊
  python quickstart_viz.py --N 500       # 自訂粒子數
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
    parser.add_argument("--box-size", type=float, help="Box 大小（覆蓋 demo 預設）")

    args = parser.parse_args()

    # Demo 配置
    configs = {
        1: {"N": 300, "beta": 0.5, "box_size": 50.0, "name": "標準配置"},
        2: {"N": 300, "beta": 2.0, "box_size": 50.0, "name": "高對齊配置"},
        3: {"N": 300, "beta": 0.0, "box_size": 50.0, "name": "混亂配置"},
        4: {"N": 500, "beta": 1.0, "box_size": 70.0, "name": "大規模配置"},
        5: {
            "N": 300,
            "beta": 1.5,
            "box_size": 50.0,
            "name": "強吸引配置",
            "Ca": 3.0,
            "la": 5.0,
            "rc": 20.0,
            "alpha": 1.0,
        },
    }

    config = configs[args.demo]

    # 應用命令列覆蓋
    if args.N:
        config["N"] = args.N
    if args.beta is not None:
        config["beta"] = args.beta
    if args.box_size:
        config["box_size"] = args.box_size

    print("\n" + "=" * 70)
    print(f"  啟動 Demo {args.demo}: {config['name']}")
    print("=" * 70)

    # 建立參數
    params_dict = {
        "Ca": config.get("Ca", 1.5),
        "Cr": 2.0,
        "la": config.get("la", 2.5),
        "lr": 0.5,
        "rc": config.get("rc", 15.0),
        "alpha": config.get("alpha", 2.0),
        "v0": 1.0,
        "beta": config["beta"],
        "box_size": config["box_size"],
        "use_pbc": True,
    }

    params = FlockingParams(**params_dict)

    # 建立系統
    system = OptimizedFlockingV2(N=config["N"], params=params)
    system.initialize(box_size=config["box_size"] * 0.1, seed=42)

    print(f"\n✅ 系統已初始化：N={config['N']}, beta={config['beta']}")

    # 建立視覺化器
    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
    )

    # 執行
    viz.run(steps=0, dt=0.01)


if __name__ == "__main__":
    main()
