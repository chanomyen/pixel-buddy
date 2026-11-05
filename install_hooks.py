"""Install / uninstall Pixel Buddy hooks in ~/.claude/settings.json.

    python install_hooks.py                 # HTTP hooks (default, no extra process per event)
    python install_hooks.py --mode command  # command hooks (fallback for older Claude Code)
    python install_hooks.py --uninstall
    python install_hooks.py --dry-run

A backup is saved next to settings.json before any change. Re-running is safe.
(The tray menu of the app does the same thing: see pixel_buddy/hooks.py.)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pixel_buddy import hooks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("http", "command"), default="http")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--settings", type=Path, default=hooks.SETTINGS)
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        cfg = hooks.read(a.settings)
    except ValueError as e:
        print(f"อ่าน {a.settings} ไม่ได้ (JSON ไม่ถูกต้อง): {e}")
        return 1
    if a.dry_run:
        print(hooks.render(cfg, a.port, a.mode, a.uninstall))
        return 0
    bak = hooks.apply(a.port, a.mode, a.uninstall, a.settings)
    if bak:
        print(f"สำรองไฟล์เดิมไว้ที่ {bak}")
    print(("ถอนการติดตั้ง hooks แล้ว" if a.uninstall else f"ติดตั้ง hooks ({a.mode}) แล้ว") + f" → {a.settings}")
    print("เปิด session Claude Code ใหม่ (หรือพิมพ์ /hooks ใน Claude Code เพื่อตรวจสอบ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
