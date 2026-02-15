"""tests/test_config.py - YAML 設定檔載入器測試"""
import pytest
from src.config import load_config, list_configs, _to_params


def test_list_configs_returns_yaml_names():
    names = list_configs()
    assert "default" in names
    assert "predator_heavy" in names
    assert "foraging_only" in names


def test_load_config_default():
    params = load_config("default")
    assert params["N"] == 100
    assert params["systemType"] == "Heterogeneous"
    assert "agentConfig" in params
    assert len(params["resources"]) > 0


def test_load_config_predator_heavy():
    params = load_config("predator_heavy")
    assert params["agentConfig"]["predatorRatio"] == 0.15


def test_load_config_foraging_only():
    params = load_config("foraging_only")
    assert params["agentConfig"]["predatorRatio"] == 0.0


def test_load_config_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config_xyz")


def test_to_params_resource_defaults():
    raw = {
        "simulation": {"N": 50},
        "resources": [{"position": [0, 0, 0], "amount": 100.0, "radius": 3.0, "renewable": True}],
    }
    params = _to_params(raw)
    r = params["resources"][0]
    assert r["renewable"] is True
    assert "replenishRate" in r
    assert "maxAmount" in r


def test_to_params_ratio_sum_exceeds_one_raises():
    raw = {
        "simulation": {"N": 100},
        "agents": {"explorerRatio": 0.5, "followerRatio": 0.6, "predatorRatio": 0.1},
        "resources": [],
    }
    with pytest.raises(ValueError, match="must be <= 1.0"):
        _to_params(raw)
