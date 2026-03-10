import os
import pathlib
import yaml

_CONFIG_PATH = pathlib.Path(__file__).parent / "config.yaml"

_DEFAULTS = {
    "db": {"path": "devlog.db"},
    "terminal": {
        "history_path": "~/.bash_history",
        "shell": "bash",
        "poll_interval": 5,
    },
    "log_collector": {
        "watch_paths": [],
        "error_patterns": ["ERROR", "Exception", "Traceback", "FATAL", "CRITICAL"],
        "poll_interval": 5,
    },
    "git": {"repos": []},
    "report": {"top_n": 5},
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (base is mutated)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _resolve_path(value: str) -> str:
    """Expand ~ and environment variables in path strings."""
    return os.path.expandvars(os.path.expanduser(value))


def load_config() -> dict:
    """Load config.yaml and merge with defaults. Returns resolved config dict."""
    import copy

    config = copy.deepcopy(_DEFAULTS)

    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(config, user_config)

    # Resolve path fields
    config["db"]["path"] = _resolve_path(str(config["db"]["path"]))
    config["terminal"]["history_path"] = _resolve_path(
        str(config["terminal"]["history_path"])
    )
    config["log_collector"]["watch_paths"] = [
        _resolve_path(p) for p in config["log_collector"]["watch_paths"]
    ]

    return config


# Module-level singleton — import CONFIG everywhere
CONFIG = load_config()

