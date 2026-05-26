"""Settings management — API keys and preferences."""

import os
from pathlib import Path

import yaml

_CONFIG_DIR = Path.home() / ".briefer"
_CONFIG_FILE = _CONFIG_DIR / "config.yaml"

# Keys that can be set via `briefer config --set`
KNOWN_KEYS = {
    "FRED_API_KEY",
    "EIA_API_KEY",
    "BLS_API_KEY",
    "ANTHROPIC_API_KEY",
    "BRIEFER_DB_PATH",
}


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_config(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


def get_key(name: str) -> str | None:
    """Resolve a config key: env var first, then config file."""
    val = os.getenv(name)
    if val:
        return val
    cfg = _load_config()
    return cfg.get("api_keys", {}).get(name)


def set_key(name: str, value: str) -> None:
    """Write a key to the config file."""
    cfg = _load_config()
    cfg.setdefault("api_keys", {})[name] = value
    _save_config(cfg)


def get_all_settings() -> dict:
    """Return merged view of all settings (env + file)."""
    cfg = _load_config()
    file_keys = cfg.get("api_keys", {})
    result = {}
    for key in KNOWN_KEYS:
        env_val = os.getenv(key)
        file_val = file_keys.get(key)
        if env_val:
            result[key] = {"value": _mask(env_val), "source": "env"}
        elif file_val:
            result[key] = {"value": _mask(file_val), "source": "config"}
        else:
            result[key] = {"value": None, "source": "not set"}
    return result


def _mask(val: str) -> str:
    if len(val) <= 8:
        return "****"
    return val[:4] + "…" + val[-4:]
