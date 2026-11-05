"""Install / uninstall Pixel Buddy hooks in ~/.claude/settings.json.

    python install_hooks.py                 # HTTP hooks (default, no extra process per event)
    python install_hooks.py --mode command  # command hooks (fallback for older Claude Code)
    python install_hooks.py --uninstall
    python install_hooks.py --dry-run

A backup is saved next to settings.json before any change. Re-running is safe.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
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
    if mode == "http":
        return {"type": "http", "url": f"http://127.0.0.1:{port}/buddy-event", "timeout": 3}
    # forward slashes work in Git Bash, cmd and PowerShell alike
    py = Path(sys.executable).as_posix()
    script = (HERE / "buddy_hook.py").as_posix()
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("http", "command"), default="http")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--settings", type=Path, default=Path.home() / ".claude" / "settings.json")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = {}
    if a.settings.exists():
        try:
            cfg = json.loads(a.settings.read_text(encoding="utf-8") or "{}")
        except ValueError as e:
            print(f"อ่าน {a.settings} ไม่ได้ (JSON ไม่ถูกต้อง): {e}")
            return 1
    hooks = cfg.setdefault("hooks", {})
    strip_ours(hooks)
    if not a.uninstall:
        for event, matcher in EVENTS.items():
            group = {"hooks": [make_hook(a.mode, a.port)]}
            if matcher:
                group = {"matcher": matcher, **group}
            hooks.setdefault(event, []).append(group)
    if not hooks:
        del cfg["hooks"]

    out = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
    if a.dry_run:
        print(out)
        return 0
    a.settings.parent.mkdir(parents=True, exist_ok=True)
    if a.settings.exists():
        bak = a.settings.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(a.settings, bak)
        print(f"สำรองไฟล์เดิมไว้ที่ {bak}")
    a.settings.write_text(out, encoding="utf-8")
    print(("ถอนการติดตั้ง hooks แล้ว" if a.uninstall else f"ติดตั้ง hooks ({a.mode}) แล้ว") + f" → {a.settings}")
    print("เปิด session Claude Code ใหม่ (หรือพิมพ์ /hooks ใน Claude Code เพื่อตรวจสอบ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
