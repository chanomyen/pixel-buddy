"""User settings, stored per-user in %APPDATA%\\PixelBuddy (never next to the exe: the install dir may be read-only).

No Qt in here.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .core import DEFAULT_PORT

APP_NAME = "PixelBuddy"
DEFAULTS = {"skin": "cat", "port": DEFAULT_PORT}


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def skins_dir() -> Path:
    d = data_dir() / "skins"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        raw = json.loads((data_dir() / "config.json").read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            cfg.update({k: raw[k] for k in DEFAULTS if k in raw})
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg: dict) -> None:
    try:
        (data_dir() / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass


def port(cfg: dict) -> int:
    """Env var PIXEL_BUDDY_PORT wins over config.json."""
    try:
        return int(os.environ.get("PIXEL_BUDDY_PORT") or cfg.get("port") or DEFAULT_PORT)
    except (TypeError, ValueError):
        return DEFAULT_PORT


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
