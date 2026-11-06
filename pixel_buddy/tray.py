"""Tray icon + the one persistent menu (also used for right-click on a critter)."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QActionGroup, QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon

from . import __version__, autostart, config, hooks, skins, updater

HOOK_LABEL = {"none": "not installed", "ok": "installed", "stale": "installed but port mismatch / incomplete"}
UPDATE_INTERVAL = 24 * 3600     # min seconds between automatic checks


class TrayController(QObject):
    _update_result = Signal(object, bool)       # (updater.fetch_latest() result, user-initiated)

    def __init__(self, app: QApplication, win, cfg: dict, port: int) -> None:
        super().__init__(app)
        self.win, self.cfg, self.port = win, cfg, port
        self.menu = QMenu()
        self.menu.aboutToShow.connect(self.rebuild)
        self.skin_menu = QMenu("Buddy (skin)", self.menu)
        self.skin_group = QActionGroup(self.skin_menu)
        self.skin_group.setExclusive(True)
        self.hooks_menu = QMenu(self.menu)
        win.menu = self.menu

        self.update: tuple[str, str] | None = None   # (version, url) when a newer release exists
        self._checking = False
        self._update_msg = False
        self._update_result.connect(self._on_update_result)
        # first check shortly after start, then re-evaluate hourly (actual network call throttled to 24h)
        QTimer.singleShot(10_000, self._auto_check)
        QTimer(self, interval=3600_000, timeout=self._auto_check).start()

        self.tray: QSystemTrayIcon | None = None
        self._retry = QTimer(self, interval=3000, timeout=self._try_show)
        self._try_show()
        if self.tray is None:          # early at login the shell may not have a tray yet
            self._retry.start()

    # ---- tray ----------------------------------------------------------
    def _try_show(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._retry.stop()
        self.tray = QSystemTrayIcon(self._icon(), self.parent())
        self.tray.setToolTip("Pixel Buddy")
        self.tray.setContextMenu(self.menu)
        self.tray.messageClicked.connect(self._message_clicked)
        self.tray.show()

    def _icon(self) -> QIcon:
        return QIcon(self.win.skin.tray_icon())

    def notify(self, text: str, update: bool = False) -> None:
        self._update_msg = update       # messageClicked only opens the download page for update toasts
        if self.tray:
            self.tray.showMessage("Pixel Buddy", text, QSystemTrayIcon.Information, 4000)

    # ---- menu ----------------------------------------------------------
    def rebuild(self) -> None:
        m = self.menu
        m.clear()
        if self.update:
            m.addAction(f"⬆ Update available: v{self.update[0]} (you have v{__version__})", self.open_update)
            m.addSeparator()
        real = [v for v in self.win.views if v.sid != "_none"]
        for v in real:
            m.addAction(v.text.replace("\n", " — ")).setEnabled(False)
        if not real:
            m.addAction("No sessions yet").setEnabled(False)
        m.addSeparator()

        self._fill_skins()
        m.addMenu(self.skin_menu)

        a = m.addAction("Run at Windows startup")
        a.setCheckable(True)
        a.setChecked(autostart.is_enabled())
        a.triggered.connect(self.toggle_autostart)

        st = hooks.status(self.port)
        hm = self.hooks_menu
        hm.clear()
        hm.setTitle(f"Claude Code hooks: {HOOK_LABEL[st]}")
        m.addMenu(hm)
        hm.addAction("Install / update hooks" if st != "none" else "Install hooks", self.install_hooks)
        rm = hm.addAction("Remove hooks", self.uninstall_hooks)
        rm.setEnabled(st != "none")
        m.addSeparator()

        a = m.addAction("Check for updates automatically")
        a.setCheckable(True)
        a.setChecked(bool(self.cfg.get("check_updates", True)))
        a.triggered.connect(self.toggle_auto_update)
        m.addAction("Check for updates now", lambda: self.check_updates(manual=True))
        m.addSeparator()
        m.addAction(f"Quit (v{__version__})", QApplication.quit)

    def _fill_skins(self) -> None:
        self.win.skins, errors = skins.discover()
        if self.win.skin.id not in self.win.skins:
            self.win.set_skin("cat")
        sm = self.skin_menu
        sm.clear()
        for sk in self.win.skins.values():
            act = sm.addAction(sk.name if sk.builtin else f"{sk.name} (mine)")
            act.setCheckable(True)
            act.setChecked(sk.id == self.win.skin.id)
            self.skin_group.addAction(act)
            act.triggered.connect(lambda _=False, sid=sk.id: self.choose_skin(sid))
        for e in errors:
            sm.addAction(f"⚠ unusable — {e}").setEnabled(False)
        sm.addSeparator()
        sm.addAction("Import skin… (.png / .zip)", self.import_skin)
        sm.addAction("Open skins folder", lambda: os.startfile(str(config.skins_dir())))

    # ---- actions -------------------------------------------------------
    def choose_skin(self, sid: str) -> None:
        self.win.set_skin(sid)
        self.cfg["skin"] = sid
        config.save(self.cfg)
        if self.tray:
            self.tray.setIcon(self._icon())

    def import_skin(self) -> None:
        path, _ = QFileDialog.getOpenFileName(None, "Import skin", str(Path.home()),
                                              "Skins (*.png *.zip skin.json);;All files (*)")
        if not path:
            return
        sid, err = skins.import_skin(Path(path))
        if sid is None:
            QMessageBox.warning(None, "Pixel Buddy", f"Skin import failed\n{err}")
            return
        self.win.skins, _ = skins.discover()
        self.choose_skin(sid)
        self.notify("Skin imported and applied")

    def toggle_autostart(self, on: bool) -> None:
        if not autostart.set_enabled(on):
            QMessageBox.warning(None, "Pixel Buddy", "Failed to set run-at-startup")

    def install_hooks(self) -> None:
        try:
            bak = hooks.apply(self.port)
        except (OSError, ValueError) as e:
            QMessageBox.warning(None, "Pixel Buddy", f"Failed to install hooks\n{e}")
            return
        self.notify("Hooks installed — open a new Claude Code session"
                    + (f"\nBackup of the original saved at {bak.name}" if bak else ""))

    def uninstall_hooks(self) -> None:
        if QMessageBox.question(None, "Pixel Buddy", "Remove Pixel Buddy hooks from ~/.claude/settings.json ?"
                                ) != QMessageBox.Yes:
            return
        try:
            hooks.apply(self.port, uninstall=True)
        except (OSError, ValueError) as e:
            QMessageBox.warning(None, "Pixel Buddy", f"Failed to remove hooks\n{e}")
            return
        self.notify("Hooks removed")

    # ---- updates -------------------------------------------------------
    def toggle_auto_update(self, on: bool) -> None:
        self.cfg["check_updates"] = on
        config.save(self.cfg)

    def _auto_check(self) -> None:
        if not self.cfg.get("check_updates", True):
            return
        if time.time() - float(self.cfg.get("last_update_check") or 0) < UPDATE_INTERVAL:
            return
        self.check_updates(manual=False)

    def check_updates(self, manual: bool) -> None:
        if self._checking:
            return
        self._checking = True
        if manual:
            self.notify("Checking for updates…")

        def work() -> None:
            self._update_result.emit(updater.fetch_latest(), manual)
        threading.Thread(target=work, daemon=True, name="update-check").start()

    def _on_update_result(self, result, manual: bool) -> None:
        self._checking = False
        if result is not None:       # network failures don't count, so we retry at the next hourly tick
            self.cfg["last_update_check"] = time.time()
            config.save(self.cfg)
        if result is None:
            if manual:
                QMessageBox.warning(None, "Pixel Buddy", "Could not check for updates.\nAre you online?")
            return
        version, url = result
        if updater.is_newer(version):
            first = self.update is None or self.update[0] != version
            self.update = (version, url)
            if first or manual:
                self.notify(f"Update available: v{version} (you have v{__version__}).\nClick to open the download page.", update=True)
        else:
            self.update = None
            if manual:
                self.notify(f"You're up to date (v{__version__})")

    def _message_clicked(self) -> None:
        if self.update and self._update_msg:
            self.open_update()

    def open_update(self) -> None:
        if self.update:
            QDesktopServices.openUrl(QUrl(self.update[1]))
