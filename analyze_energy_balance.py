"""
系統能量平衡分析腳本

計算：
1. 總能量消耗速率（所有 agents）
2. 總能量補充速率（所有資源）
3. 達到平衡所需的資源配置

目標：讓系統長期穩定運行，agents 不會全部餓死
"""

import numpy as np

# ===== 當前系統參數 =====

# Agent 設定
N_agents = 100
energy_consumption_rate = 0.2  # 每 agent 每步消耗

# 資源設定（來自 simulation_manager.py 的預設值）
resources = [
    {
        "name": "Resource 1 (Renewable)",
        "position": [15.0, 15.0, 0.0],
        "amount": 200.0,
        "radius": 4.0,
        "renewable": True,
        "replenish_rate": 10.0,
        "max_amount": 300.0,
    },
    {
        "name": "Resource 2 (Consumable)",
        "position": [-15.0, -15.0, 0.0],
        "amount": 500.0,
        "radius": 5.0,
        "renewable": False,
        "replenish_rate": 0.0,
        "max_amount": 500.0,
    },
    {
        "name": "Resource 3 (Renewable)",
        "position": [0.0, 20.0, 10.0],
        "amount": 200.0,
        "radius": 4.0,
        "renewable": True,
        "replenish_rate": 10.0,
        "max_amount": 300.0,
    },
]

# ===== 分析 =====

print("=" * 80)
print("系統能量平衡分析")
print("=" * 80)

# 1. 計算總消耗速率
total_consumption_per_step = N_agents * energy_consumption_rate

print(f"\n【能量消耗】")
print(f"  Agents 數量: {N_agents}")
print(f"  每 agent 每步消耗: {energy_consumption_rate:.2f} energy")
print(f"  總消耗速率: {total_consumption_per_step:.2f} energy/step")

# 2. 計算總補充速率
total_replenish_per_step = sum(r["replenish_rate"] for r in resources)

print(f"\n【能量補充】")
print(f"  資源數量: {len(resources)}")
for i, res in enumerate(resources, 1):
    renewable_str = "✓ Renewable" if res["renewable"] else "✗ Consumable"
    print(f"  Resource {i}: {res['replenish_rate']:.1f} energy/step  {renewable_str}")
print(f"  總補充速率: {total_replenish_per_step:.2f} energy/step")

# 3. 平衡分析
balance = total_replenish_per_step - total_consumption_per_step

print(f"\n【平衡分析】")
print(f"  淨能量流: {balance:+.2f} energy/step")

if balance > 0:
    print(f"  ✅ 系統有盈餘（+{balance:.2f} energy/step）")
    print(f"  → Agents 可以長期存活")
elif balance == 0:
    print(f"  ⚖️  系統完美平衡")
    print(f"  → Agents 能量穩定，但無成長空間")
else:
    print(f"  ❌ 系統虧損（{balance:.2f} energy/step）")
    deficit_per_step = -balance

    # 計算可消耗資源總量
    consumable_total = sum(r["amount"] for r in resources if not r["renewable"])

    if consumable_total > 0:
        # 有消耗性資源可以延緩死亡
        steps_until_depletion = consumable_total / deficit_per_step
        print(f"  → 消耗性資源總量: {consumable_total:.1f} energy")
        print(
            f"  → 可維持約 {steps_until_depletion:.0f} 步（{steps_until_depletion * 0.1:.1f} 秒，dt=0.1）"
        )
        print(f"  → 之後 agents 將逐漸餓死")
    else:
        print(f"  → 無消耗性資源緩衝")
        print(f"  → Agents 將快速餓死")

# 4. 推薦方案
print(f"\n{'=' * 80}")
print("推薦調整方案")
print("=" * 80)

required_replenish = total_consumption_per_step * 1.1  # 110% 確保盈餘
current_replenish = total_replenish_per_step
multiplier = (
    required_replenish / current_replenish if current_replenish > 0 else float("inf")
)

print(f"\n目標：總補充速率 = {required_replenish:.2f} energy/step (110% 消耗)")
print(f"當前：總補充速率 = {current_replenish:.2f} energy/step")
print(f"需要：{multiplier:.2f}x 當前補充速率")

# 方案 A：等比例增加所有資源補充率
print(f"\n【方案 A】等比例提升所有資源補充率（{multiplier:.2f}x）")
for i, res in enumerate(resources, 1):
    if res["renewable"]:
        new_rate = res["replenish_rate"] * multiplier
        print(
            f"  Resource {i}: {res['replenish_rate']:.1f} → {new_rate:.1f} energy/step"
        )

# 方案 B：新增資源點
n_new_resources = int(np.ceil((required_replenish - current_replenish) / 10.0))
print(f"\n【方案 B】新增 {n_new_resources} 個再生資源（replenish_rate=10.0）")
print(f"  位置可分散在空間中以避免擁擠")

# 方案 C：降低消耗率
new_consumption_rate = total_replenish_per_step / (N_agents * 1.1)
print(f"\n【方案 C】降低能量消耗率")
print(
    f"  當前: {energy_consumption_rate:.2f} → 建議: {new_consumption_rate:.3f} energy/step"
)
print(f"  減少 {(1 - new_consumption_rate / energy_consumption_rate) * 100:.1f}%")

# 方案 D：混合調整
print(f"\n【方案 D】混合調整（推薦）")
balanced_multiplier = np.sqrt(multiplier)  # 平衡兩者
new_replenish = res["replenish_rate"] * balanced_multiplier if res["renewable"] else 0
new_consumption = energy_consumption_rate / balanced_multiplier

print(f"  1. 補充率提升 {balanced_multiplier:.2f}x")
for i, res in enumerate(resources, 1):
    if res["renewable"]:
        new_rate = res["replenish_rate"] * balanced_multiplier
        print(f"     Resource {i}: {res['replenish_rate']:.1f} → {new_rate:.1f}")

print(f"  2. 消耗率降低 {balanced_multiplier:.2f}x")
print(f"     Agent consumption: {energy_consumption_rate:.2f} → {new_consumption:.3f}")

# 驗證
new_total_replenish = sum(
    r["replenish_rate"] * balanced_multiplier if r["renewable"] else 0
    for r in resources
)
new_total_consumption = N_agents * new_consumption
new_balance = new_total_replenish - new_total_consumption
print(f"\n  驗證：")
print(f"    新補充率: {new_total_replenish:.2f} energy/step")
print(f"    新消耗率: {new_total_consumption:.2f} energy/step")
print(f"    淨能量流: {new_balance:+.2f} energy/step")
print(f"    {'✅ 達到平衡！' if new_balance >= 0 else '❌ 仍有虧損'}")

print(f"\n{'=' * 80}")
print("執行建議")
print("=" * 80)
print("""
1. 最簡單：採用【方案 A】，在 simulation_manager.py 中調整 replenishRate
2. 最彈性：採用【方案 D】，同時調整補充率與消耗率
3. 長期優化：根據實際觀測調整，確保生態系統穩定

修改位置：
  - 補充率: backend/simulation_manager.py (L57, L74)
  - 消耗率: src/flocking_heterogeneous.py (L181)
""")
