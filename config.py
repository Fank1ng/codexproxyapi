"""Configuration management — reads and writes config.json."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "port": 8800,
    "rate_limit_cooldown": 60,
    "rotation_strategy": "round_robin",
    "max_retries": 10,
    "quota_refresh_interval": 300,
    "log_level": "INFO",
}


def load() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    else:
        cfg = {}
    return {**DEFAULTS, **cfg}


def save(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str):
    cfg = load()
    return cfg.get(key, DEFAULTS.get(key))
