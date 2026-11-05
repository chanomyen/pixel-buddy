"""Run-at-login via HKCU\\...\\Run (no admin needed). No-ops off Windows."""
from __future__ import annotations

import sys
from pathlib import Path

from .config import APP_NAME, frozen

IS_WIN = sys.platform == "win32"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
ROOT = Path(__file__).resolve().parent.parent


def command() -> str:
    if frozen():
        return f'"{sys.executable}"'
    # dev: pythonw (no console window) + buddy.pyw
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    return f'"{pyw if pyw.exists() else py}" "{ROOT / "buddy.pyw"}"'


def is_enabled() -> bool:
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_enabled(on: bool) -> bool:
    """Returns True on success."""
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
