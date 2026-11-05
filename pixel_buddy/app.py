"""Overlay window: pixel-art critters that live on top of the Windows taskbar."""
from __future__ import annotations

import os
import random
import sys
import time

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QToolTip, QWidget

from . import sprites, taskbar
from .core import DEFAULT_PORT, Manager, View, start_server

WIN_H = 120        # overlay height in px
FEET_SINK = 2      # feet sink this many px into the taskbar so they look like they stand on it
ICON_SCALE = 3
SCALE = {"haiku": 3}  # default 4; Haiku is the small, nimble one
SPEED = {"idle": 22, "thinking": 16, "tool": 70}   # px / second
IDLE_VIEW = View("_none", "", "sleep", "", "unknown", "", 0, "Claude Code: ยังไม่มี session ที่ทำงานอยู่\n(เริ่ม claude แล้วน้องจะตื่น)")


class Actor:
    def __init__(self, x: float) -> None:
        self.x = x
        self.dir = 1
        self.target = x
        self.pause = random.uniform(0, 2)
        self.moving = False
        self.speed = 0.0
        self.seed = random.randrange(1000)
        self.rect = QRect()
        self.view: View = IDLE_VIEW

    def step(self, dt: float, v: View, max_x: float) -> None:
        self.moving = False
        self.x = min(max(0.0, self.x), max_x)
        speed = SPEED.get(v.state, 0)
        if v.state == "tool" and v.kind == "bash":
            speed = 130
        if speed == 0:
            return
        if self.pause > 0:
            self.pause -= dt
            return
        d = self.target - self.x
        if abs(d) < 2:
            self.pause = random.uniform(1.5, 5) if v.state in ("idle", "thinking") else random.uniform(0, 0.4)
            self.target = random.uniform(8, max(9.0, max_x))
            return
        self.dir = 1 if d > 0 else -1
        self.x += self.dir * min(abs(d), speed * dt)
        self.moving, self.speed = True, speed


def pose_for(a: Actor, v: View) -> str:
    return {"sleep": "sleep", "alert": "alert", "done": "happy", "error": "error"}.get(
        v.state, ("run" if a.speed >= 100 else "walk") if a.moving else "sit")


class Overlay(QWidget):
    def __init__(self, mgr: Manager) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
        self.mgr = mgr
        self.actors: dict[str, Actor] = {}
        self.views: list[View] = []
        self._cache: dict[tuple, QPixmap] = {}
        self._last = time.time()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.place()

        self.timer = QTimer(self, interval=33, timeout=self.tick)
        self.timer.start()
        self.slow = QTimer(self, interval=1000, timeout=self.slow_tick)
        self.slow.start()

    # ---- geometry ------------------------------------------------------
    def place(self) -> None:
        scr = QGuiApplication.primaryScreen()
        ag = scr.availableGeometry()           # excludes the taskbar
        top = ag.bottom() + 1                  # = top edge of a bottom taskbar
        self.setGeometry(ag.left(), top - WIN_H + FEET_SINK, ag.width(), WIN_H)

    def slow_tick(self) -> None:
        if taskbar.fullscreen_app_active():
            if self.isVisible():
                self.hide()
            return
        if not self.isVisible():
            self.show()
        self.place()
        taskbar.keep_on_top(int(self.winId()))

    # ---- simulation ----------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        dt = min(0.1, now - self._last)
        self._last = now
        self.views = self.mgr.views(now) or [IDLE_VIEW]
        ids = {v.sid for v in self.views}
        for sid in [k for k in self.actors if k not in ids]:
            del self.actors[sid]
        for v in self.views:
            a = self.actors.get(v.sid)
            if a is None:
                a = self.actors[v.sid] = Actor(random.uniform(40, max(60, self.width() - 100)))
            a.view = v
            a.step(dt, v, max(0.0, self.width() - 16 * SCALE.get(v.family, 4) - 8))
        self.update()

    # ---- drawing -------------------------------------------------------
    def _pix(self, key: tuple, grid, pal: dict[str, str], scale: int, flip: bool) -> QPixmap:
        pm = self._cache.get(key)
        if pm is None:
            w, h = len(grid[0]), len(grid)
            img = QImage(w * scale, h * scale, QImage.Format_ARGB32_Premultiplied)
            img.fill(0)
            p = QPainter(img)
            for y, row in enumerate(grid):
                for x, ch in enumerate(row):
                    if ch != "." and ch in pal:
                        xx = (w - 1 - x) if flip else x
                        p.fillRect(xx * scale, y * scale, scale, scale, QColor(pal[ch]))
            p.end()
            pm = self._cache[key] = QPixmap.fromImage(img)
        return pm

    def _critter(self, fr: sprites.Frame, fam: str, scale: int, flip: bool) -> QPixmap:
        return self._pix(("c", fr.key, fam, scale, flip), fr.grid, sprites.palette(fam), scale, flip)

    def paintEvent(self, _event) -> None:
        tick = int(time.time() * 8)
        p = QPainter(self)
        for a in self.actors.values():
            self._draw_actor(p, a, tick)

    def _draw_tag(self, p: QPainter, v: View, x: int, y: int, scale: int, flip: bool, sleeping: bool) -> None:
        """First 2 letters of the project name, printed on the cat's chest."""
        tag = "".join(c for c in v.project if c.isascii() and c.isalnum())[:2].upper()
        if not tag:
            return
        font = QFont("Consolas")
        font.setPixelSize(max(8, scale * 3))
        font.setBold(True)
        font.setStyleStrategy(QFont.NoAntialias)    # crisp, matches the pixel art
        p.setFont(font)
        # chest = interior cols 3..11, rows 6..9 (sleeping loaf: shifted down 2 rows, 1 row shorter)
        col0 = 4 if flip else 3                      # mirrored sprite shifts the interior by one cell
        row0, rows = (8, 3) if sleeping else (6, 4)
        r = QRect(x + col0 * scale, y + row0 * scale, 9 * scale, rows * scale)
        p.setPen(QColor(255, 255, 255, 110))
        p.drawText(r.translated(0, 1), Qt.AlignCenter, tag)
        p.setPen(QColor("#2b1d14"))
        p.drawText(r, Qt.AlignCenter, tag)

    def _draw_actor(self, p: QPainter, a: Actor, tick: int) -> None:
        v = a.view
        scale = SCALE.get(v.family, 4)
        t = tick + a.seed
        flip = a.dir < 0

        # subagents trail behind as tiny critters
        for i in range(min(v.agents, 4)):
            mini = sprites.build("run" if a.moving else "sit", t + i, v.family)
            pm = self._critter(mini, v.family, 2, flip)
            fx = a.x - a.dir * (14 + 18 * i) + (8 * scale - 16)
            p.drawPixmap(int(fx), int(self.height() - pm.height() - mini.yoff * 2), pm)

        fr = sprites.build(pose_for(a, v), t, v.family)
        pm = self._critter(fr, v.family, scale, flip)
        x = int(a.x)
        y = int(self.height() - pm.height() - fr.yoff * scale)
        p.drawPixmap(x, y, pm)
        a.rect = QRect(x, y, pm.width(), pm.height())
        self._draw_tag(p, v, x, y, scale, flip, sleeping=pose_for(a, v) == "sleep")

        cx = x + pm.width() // 2
        icon = sprites.icon_for(v.state, v.kind)
        iy = y - sprites.ICON * ICON_SCALE - 6 - (1 if tick % 4 < 2 else 0) * 2
        if icon:
            ipm = self._pix(("i", v.state, v.kind), icon, sprites.palette("sonnet"), ICON_SCALE, False)
            p.drawPixmap(cx - ipm.width() // 2, iy, ipm)
        elif v.state == "thinking":
            n = (t // 3) % 4
            for k in range(n):
                px = cx - 12 + k * 9
                p.fillRect(px + 1, iy + 15, 5, 5, QColor(0, 0, 0, 110))
                p.fillRect(px, iy + 14, 5, 5, QColor("#ffffff"))
        elif v.state == "sleep":
            p.setFont(QFont("Consolas", 11, QFont.Bold))
            for k, ch in enumerate("zZ"):
                off = ((t // 4) + k * 2) % 6
                p.setPen(QColor(0, 0, 0, 120))
                p.drawText(cx + 9 + k * 9, y - 2 - off + 1, ch)
                p.setPen(QColor("#ffffff"))
                p.drawText(cx + 8 + k * 9, y - 2 - off, ch)

    # ---- interaction ---------------------------------------------------
    def _actor_at(self, pos: QPoint) -> Actor | None:
        for a in self.actors.values():
            if a.rect.contains(pos):
                return a
        return None

    def mouseMoveEvent(self, e) -> None:
        a = self._actor_at(e.position().toPoint())
        if a:
            QToolTip.showText(e.globalPosition().toPoint(), a.view.text, self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            a = self._actor_at(e.position().toPoint())
            if a:
                QToolTip.showText(e.globalPosition().toPoint(), a.view.text, self, QRect(), 6000)

    def contextMenuEvent(self, e) -> None:
        self.build_menu().exec(e.globalPos())

    def build_menu(self) -> QMenu:
        m = QMenu()
        real = [v for v in self.views if v.sid != "_none"]
        for v in real:
            act = QAction(v.text.replace("\n", " — "), m)
            act.setEnabled(False)
            m.addAction(act)
        if not real:
            act = QAction("ยังไม่มี session", m)
            act.setEnabled(False)
            m.addAction(act)
        m.addSeparator()
        m.addAction("ออก (Quit)", QApplication.quit)
        return m


def main() -> None:
    port = int(os.environ.get("PIXEL_BUDDY_PORT", DEFAULT_PORT))
    mgr = Manager()
    try:
        start_server(mgr, port)
    except OSError:
        print(f"พอร์ต {port} ถูกใช้อยู่ — เปิด Pixel Buddy ซ้ำหรือเปล่า? (ตั้ง PIXEL_BUDDY_PORT เพื่อเปลี่ยนพอร์ต)")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = Overlay(mgr)
    win.show()

    tray_pm = win._critter(sprites.build("sit", 0, "sonnet"), "sonnet", 2, False)
    tray = QSystemTrayIcon(QIcon(tray_pm), app)
    tray.setToolTip("Pixel Buddy")
    tray.setContextMenu(win.build_menu())
    menu_refresh = QTimer(interval=2000, timeout=lambda: tray.setContextMenu(win.build_menu()))
    menu_refresh.start()
    tray.show()

    print(f"Pixel Buddy พร้อมแล้ว — รับ hook ที่ http://127.0.0.1:{port}")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
