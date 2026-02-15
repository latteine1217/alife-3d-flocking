"""
YAML 實驗設定檔載入器

What: 讀取 YAML 設定檔，轉換為 backend SimulationManager 接受的 params dict
Why: 讓不同實驗場景可重現，避免參數散落在程式碼中
"""

import yaml
from pathlib import Path


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
