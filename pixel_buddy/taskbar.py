"""Small Windows-only helpers (all no-ops on other platforms)."""
from __future__ import annotations

import ctypes
import sys

IS_WIN = sys.platform == "win32"


def keep_on_top(hwnd: int) -> None:
    """Windows 11 sometimes lifts the taskbar over topmost windows; re-assert our z-order."""
    if not IS_WIN or not hwnd:
        return
    HWND_TOPMOST = -1
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x1, 0x2, 0x10, 0x40
    try:
        ctypes.windll.user32.SetWindowPos(
            ctypes.c_void_p(hwnd), ctypes.c_void_p(HWND_TOPMOST), 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
    except Exception:
        pass


def fullscreen_app_active() -> bool:
    """True when a full-screen app / game / presentation is in front (hide the critters then)."""
    if not IS_WIN:
        return False
    try:
        state = ctypes.c_int(0)
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) == 0:
            # 2 = busy (fullscreen), 3 = D3D fullscreen, 4 = presentation mode
            return state.value in (2, 3, 4)
    except Exception:
        pass
    return False
