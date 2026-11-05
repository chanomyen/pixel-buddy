"""Tray icon + the one persistent menu (also used for right-click on a critter)."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon

from . import autostart, config, hooks, skins

HOOK_LABEL = {"none": "ยังไม่ได้ติดตั้ง", "ok": "ติดตั้งแล้ว", "stale": "ติดตั้งไว้แต่พอร์ตไม่ตรง / ไม่ครบ"}


class TrayController(QObject):
    def __init__(self, app: QApplication, win, cfg: dict, port: int) -> None:
        super().__init__(app)
        self.win, self.cfg, self.port = win, cfg, port
        self.menu = QMenu()
        self.menu.aboutToShow.connect(self.rebuild)
        self.skin_menu = QMenu("น้อง (สกิน)", self.menu)
        self.skin_group = QActionGroup(self.skin_menu)
        self.skin_group.setExclusive(True)
        self.hooks_menu = QMenu(self.menu)
        win.menu = self.menu

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
        self.tray.show()

    def _icon(self) -> QIcon:
        return QIcon(self.win.skin.tray_icon())

    def notify(self, text: str) -> None:
        if self.tray:
            self.tray.showMessage("Pixel Buddy", text, QSystemTrayIcon.Information, 4000)

    # ---- menu ----------------------------------------------------------
    def rebuild(self) -> None:
        m = self.menu
        m.clear()
        real = [v for v in self.win.views if v.sid != "_none"]
        for v in real:
            m.addAction(v.text.replace("\n", " — ")).setEnabled(False)
        if not real:
            m.addAction("ยังไม่มี session").setEnabled(False)
        m.addSeparator()

        self._fill_skins()
        m.addMenu(self.skin_menu)

        a = m.addAction("เปิดตอนเริ่ม Windows")
        a.setCheckable(True)
        a.setChecked(autostart.is_enabled())
        a.triggered.connect(self.toggle_autostart)

        st = hooks.status(self.port)
        hm = self.hooks_menu
        hm.clear()
        hm.setTitle(f"Claude Code hooks: {HOOK_LABEL[st]}")
        m.addMenu(hm)
        hm.addAction("ติดตั้ง / อัปเดต hooks" if st != "none" else "ติดตั้ง hooks", self.install_hooks)
        rm = hm.addAction("ถอน hooks", self.uninstall_hooks)
        rm.setEnabled(st != "none")
        m.addSeparator()
        m.addAction("ออก (Quit)", QApplication.quit)

    def _fill_skins(self) -> None:
        self.win.skins, errors = skins.discover()
        if self.win.skin.id not in self.win.skins:
            self.win.set_skin("cat")
        sm = self.skin_menu
        sm.clear()
        for sk in self.win.skins.values():
            act = sm.addAction(sk.name if sk.builtin else f"{sk.name} (ของฉัน)")
            act.setCheckable(True)
            act.setChecked(sk.id == self.win.skin.id)
            self.skin_group.addAction(act)
            act.triggered.connect(lambda _=False, sid=sk.id: self.choose_skin(sid))
        for e in errors:
            sm.addAction(f"⚠ ใช้ไม่ได้ — {e}").setEnabled(False)
        sm.addSeparator()
        sm.addAction("นำเข้าสกิน… (.png / .zip)", self.import_skin)
        sm.addAction("เปิดโฟลเดอร์สกิน", lambda: os.startfile(str(config.skins_dir())))

    # ---- actions -------------------------------------------------------
    def choose_skin(self, sid: str) -> None:
        self.win.set_skin(sid)
        self.cfg["skin"] = sid
        config.save(self.cfg)
        if self.tray:
            self.tray.setIcon(self._icon())

    def import_skin(self) -> None:
        path, _ = QFileDialog.getOpenFileName(None, "นำเข้าสกิน", str(Path.home()),
                                              "สกิน (*.png *.zip skin.json);;ทั้งหมด (*)")
        if not path:
            return
        sid, err = skins.import_skin(Path(path))
        if sid is None:
            QMessageBox.warning(None, "Pixel Buddy", f"นำเข้าสกินไม่สำเร็จ\n{err}")
            return
        self.win.skins, _ = skins.discover()
        self.choose_skin(sid)
        self.notify("นำเข้าสกินแล้ว และเปลี่ยนให้เรียบร้อย")

    def toggle_autostart(self, on: bool) -> None:
        if not autostart.set_enabled(on):
            QMessageBox.warning(None, "Pixel Buddy", "ตั้งค่าเปิดพร้อม Windows ไม่สำเร็จ")

    def install_hooks(self) -> None:
        try:
            bak = hooks.apply(self.port)
        except (OSError, ValueError) as e:
            QMessageBox.warning(None, "Pixel Buddy", f"ติดตั้ง hooks ไม่สำเร็จ\n{e}")
            return
        self.notify("ติดตั้ง hooks แล้ว — เปิด session Claude Code ใหม่"
                    + (f"\nสำรองไฟล์เดิมไว้ที่ {bak.name}" if bak else ""))

    def uninstall_hooks(self) -> None:
        if QMessageBox.question(None, "Pixel Buddy", "ถอน hooks ของ Pixel Buddy ออกจาก ~/.claude/settings.json ?"
                                ) != QMessageBox.Yes:
            return
        try:
            hooks.apply(self.port, uninstall=True)
        except (OSError, ValueError) as e:
            QMessageBox.warning(None, "Pixel Buddy", f"ถอน hooks ไม่สำเร็จ\n{e}")
            return
        self.notify("ถอน hooks แล้ว")
