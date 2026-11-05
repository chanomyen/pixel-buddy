# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Pixel Buddy: Windows 11 desktop overlay (PySide6). Pixel cats walk on the taskbar and mirror live Claude Code session state (one cat per session, colour = model family). README and user-facing strings (UI, CLI, installer) are in English — keep that language when editing UI/CLI text.

## Commands

No lint or test suite exists (only the optional PyInstaller/Inno build below). Windows only at runtime (uses `ctypes` Win32 calls in `taskbar.py`).

```powershell
pip install -r requirements.txt        # PySide6 only; project venv is .venv
python -m pixel_buddy                 # run overlay (or double-click buddy.pyw: no console)
python install_hooks.py [--mode command] [--port N] [--dry-run] [--uninstall]   # edit ~/.claude/settings.json (auto-backup)
python simulate.py --model claude-opus-4-1 --loop   # fake a session via HTTP; --sid/--cwd for 2nd cat, --error for failure
python preview_sprites.py              # preview sprite grids
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # PyInstaller onedir -> dist\PixelBuddy\, + Inno Setup installer if ISCC is installed (pip install -r requirements-dev.txt)
```

Port: env `PIXEL_BUDDY_PORT` > `%APPDATA%\PixelBuddy\config.json` > 7777. `install_hooks.py --port` / tray "install hooks" must match.

## Architecture

Pipeline: Claude Code hook -> HTTP POST `127.0.0.1:<port>/buddy-event` -> `Manager.handle()` -> per-session `Session` state -> `Manager.views()` polled by UI every 33ms -> `Overlay` paints.

- `pixel_buddy/core.py` — **no Qt**, testable anywhere. Event->state machine (`idle|thinking|tool|alert|done|error`), HTTP server (`start_server`, daemon thread, localhost only; GET returns views as JSON), model-name parsing. `Manager._view()` turns state into display `View` and owns time-based transitions: `done`/`error` decay to `idle` after 5/6s, `idle` -> `sleep` after 60s, stale sessions evicted in `views()`. Tooltip text is built there too.
- `pixel_buddy/app.py` — Qt `Overlay` (frameless, translucent, always-on-top, click-through transparent pixels). `Actor` = per-session movement sim; `pose_for()` maps View -> sprite pose; sprites come from the active `Skin` (`skins.py`, painted into cached `QPixmap`s). Tunables at top: `WIN_H`, `FEET_SINK`, `SPEED`. `slow_tick` (1s) re-places window, hides for fullscreen apps, re-raises z-order.
- `pixel_buddy/taskbar.py` — Win32 helpers: `fullscreen_app_active()` (`SHQueryUserNotificationState`), `keep_on_top()` (Win11 pushes taskbar above overlay).
- `pixel_buddy/sprites.py` — sprites as 16x12 char grids + 7x7 icons; `palette(family)` colours by model family; `build(pose, tick, family)` composes a frame; crown for opus/fable/mythos.
- `pixel_buddy/config.py` (settings in %APPDATA%\PixelBuddy), `autostart.py` (HKCU Run key via winreg), `hooks.py` (settings.json edit logic, shared by `install_hooks.py` CLI and tray; frozen exe forces http mode), `skins.py` (Qt: `BuiltinSkin` wraps `sprites.build(critter=...)`; `SheetSkin` loads user PNG sheets + skin.json from %APPDATA%\PixelBuddy\skins; import .png/.zip/skin.json), `tray.py` (one persistent QMenu rebuilt in `aboutToShow`, shared by tray icon and right-click). `app.main()` also handles `--cleanup` / `--install-hooks` flags used by the Inno installer (`packaging/`).
- `install_hooks.py` — thin CLI over `hooks.py`; registers 13 events; hooks identified as ours by `/buddy-event` in url or `buddy_hook.py` in command (used by strip/uninstall, so keep those markers). `http` mode default; `command` mode uses `buddy_hook.py` stdin->POST forwarder (must always exit 0, never block Claude Code).

Model detection: `model` field on SessionStart/PostModelSwitch, plus `read_model()` tails the transcript JSONL (`transcript_path`) on SessionStart/UserPromptSubmit/Stop in a background thread. Only metadata is stored, never conversation content.

## Notes

- Adding a new hook event: update `EVENTS` in `pixel_buddy/hooks.py` AND handle it in `Manager.handle()`.
- Adding a built-in skin: add a grid to `sprites.BASES` (same row/eye/chest cells as cat) + register in `skins.builtins()`. Overlay draws only through `Skin.render/tag_rect/width`; skin caches are per-skin.
- Adding a model family: `FAMILIES` in `core.py` + `FAMILY_COLORS` in `sprites.py`.
- README admits the overlay positioning was never verified on a real Windows 11 taskbar; tune `FEET_SINK`/`WIN_H` if misaligned.
