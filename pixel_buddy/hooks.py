"""Register / remove Pixel Buddy hooks in ~/.claude/settings.json. No Qt.

Used by install_hooks.py (CLI) and by the tray menu. A backup is saved before every change.
Hooks are recognised as ours by "/buddy-event" in the url or "buddy_hook.py" in the command.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

from .config import frozen

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = Path.home() / ".claude" / "settings.json"
# event -> matcher (None = event has no matcher support)
EVENTS = {
    "SessionStart": None, "SessionEnd": None, "UserPromptSubmit": None,
    "PreToolUse": "*", "PostToolUse": "*", "PostToolUseFailure": "*", "PermissionRequest": "*",
    "Notification": None, "SubagentStart": None, "SubagentStop": None,
    "Stop": None, "StopFailure": None, "PostModelSwitch": None,
}


def is_ours(hook: dict) -> bool:
    return "/buddy-event" in str(hook.get("url", "")) or "buddy_hook.py" in str(hook.get("command", ""))


def make_hook(mode: str, port: int) -> dict:
    if mode == "http" or frozen():      # command mode needs buddy_hook.py + a python: impossible in an exe
        return {"type": "http", "url": f"http://127.0.0.1:{port}/buddy-event", "timeout": 3}
    # forward slashes work in Git Bash, cmd and PowerShell alike
    py = Path(sys.executable).as_posix()
    script = (ROOT / "buddy_hook.py").as_posix()
    return {"type": "command", "command": f'"{py}" "{script}"', "timeout": 5}


def strip_ours(hooks: dict) -> None:
    for event in list(hooks):
        groups = []
        for g in hooks[event]:
            inner = [h for h in g.get("hooks", []) if not is_ours(h)]
            if inner:
                groups.append({**g, "hooks": inner})
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]


def render(cfg: dict, port: int, mode: str = "http", uninstall: bool = False) -> str:
    """New settings.json text (pure; does not touch disk)."""
    cfg = json.loads(json.dumps(cfg))
    hooks = cfg.setdefault("hooks", {})
    strip_ours(hooks)
    if not uninstall:
        for event, matcher in EVENTS.items():
            group = {"hooks": [make_hook(mode, port)]}
            if matcher:
                group = {"matcher": matcher, **group}
            hooks.setdefault(event, []).append(group)
    if not hooks:
        del cfg["hooks"]
    return json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"


def read(settings: Path = SETTINGS) -> dict:
    """Raises ValueError if the file exists but is not valid JSON."""
    if not settings.exists():
        return {}
    return json.loads(settings.read_text(encoding="utf-8") or "{}")


def apply(port: int, mode: str = "http", uninstall: bool = False, settings: Path = SETTINGS) -> Path | None:
    """Write settings. Returns the backup path (None if there was nothing to back up)."""
    out = render(read(settings), port, mode, uninstall)
    settings.parent.mkdir(parents=True, exist_ok=True)
    bak = None
    if settings.exists():
        bak = settings.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(settings, bak)
    settings.write_text(out, encoding="utf-8")
    return bak


def status(port: int, settings: Path = SETTINGS) -> str:
    """'none' = not installed, 'ok' = installed for this port, 'stale' = other port / incomplete."""
    try:
        hooks = read(settings).get("hooks", {})
    except (OSError, ValueError):
        return "none"
    found, ok = 0, 0
    for event in EVENTS:
        for g in hooks.get(event, []):
            for h in g.get("hooks", []):
                if is_ours(h):
                    found += 1
                    m = re.search(r":(\d+)/buddy-event", str(h.get("url", "")))
                    if m is None or int(m.group(1)) == port:   # command hooks read the port from env
                        ok += 1
    if not found:
        return "none"
    return "ok" if ok == found and found >= len(EVENTS) else "stale"
