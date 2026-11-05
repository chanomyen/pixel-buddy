"""Skins = the look of the critters. Two kinds:

* built-in  : char-grid art from sprites.py (cat, bunny); recoloured per Claude model family, wear a crown, etc.
* user skin : a folder in %APPDATA%\\PixelBuddy\\skins\\<name>\\ with
      sheet.png   sprite sheet, one row per pose, one column per animation frame
      skin.json   optional manifest (see README)

User skins are drawn as-is (no model-family recolour).
"""
from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from . import sprites
from .config import skins_dir

POSES = ("sit", "walk", "run", "sleep", "alert", "happy", "error")
FALLBACK = {"run": "walk", "walk": "sit", "sleep": "sit", "alert": "sit", "happy": "sit", "error": "sit"}
YOFF = {"alert": (0, 1, 2, 1), "happy": (0, 2, 3, 2)}
MAX_FRAME = 256          # px, max source frame width
MAX_H = 90               # px, max frame height (overlay window is 120px tall, minus room for the status icon)
MAX_ZIP = 20_000_000     # bytes, uncompressed


class Skin:
    id = ""
    name = ""
    builtin = False

    def scale(self, family: str) -> int:
        raise NotImplementedError

    def width(self, family: str) -> int:
        raise NotImplementedError

    def render(self, pose: str, tick: int, family: str, flip: bool, mini: bool = False) -> tuple[QPixmap, int]:
        """(pixmap, vertical bounce in px)"""
        raise NotImplementedError

    def tag_rect(self, pose: str, family: str, flip: bool) -> QRect | None:
        """Where the project tag goes, relative to the sprite's top-left; None = no tag."""
        return None

    def tray_icon(self) -> QPixmap:
        return self.render("sit", 0, "sonnet", False)[0]


# ---- built-in ------------------------------------------------------------
class BuiltinSkin(Skin):
    builtin = True

    def __init__(self, sid: str, name: str, critter: str) -> None:
        self.id, self.name, self.critter = sid, name, critter
        self._cache: dict[tuple, QPixmap] = {}

    def scale(self, family: str) -> int:
        return {"haiku": 3}.get(family, 4)

    def width(self, family: str) -> int:
        return sprites.W * self.scale(family)

    def render(self, pose, tick, family, flip, mini=False):
        scale = 2 if mini else self.scale(family)
        fr = sprites.build(pose, tick, family, self.critter)
        key = (fr.key, family, scale, flip)
        pm = self._cache.get(key)
        if pm is None:
            pm = self._cache[key] = _paint_grid(fr.grid, sprites.palette(family), scale, flip)
        return pm, fr.yoff * scale

    def tag_rect(self, pose, family, flip):
        s = self.scale(family)
        col0 = 4 if flip else 3                          # mirrored sprite shifts the interior by one cell
        row0, rows = (8, 3) if pose == "sleep" else (6, 4)   # chest = interior cols 3..11, rows 6..9
        return QRect(col0 * s, row0 * s, 9 * s, rows * s)


def _paint_grid(grid, pal: dict[str, str], scale: int, flip: bool) -> QPixmap:
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
    return QPixmap.fromImage(img)


# ---- user skins ----------------------------------------------------------
class SheetSkin(Skin):
    def __init__(self, sid: str, name: str, frames: dict[str, list[QImage]], fw: int, fh: int, scale: int,
                 chest: tuple[int, int, int, int] | None) -> None:
        self.id, self.name = sid, name
        self.frames, self.fw, self.fh, self._scale, self.chest = frames, fw, fh, scale, chest
        self._cache: dict[tuple, QPixmap] = {}

    @classmethod
    def load(cls, folder: Path, sid: str) -> "SheetSkin":
        """Raises ValueError with a (Thai) message if the folder is not a usable skin."""
        man: dict = {}
        mf = folder / "skin.json"
        if mf.exists():
            try:
                man = json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise ValueError(f"Cannot read skin.json: {e}") from e
            if not isinstance(man, dict):
                raise ValueError("skin.json must be an object")
        sheet = folder / str(man.get("sheet") or "sheet.png")
        if sheet.parent != folder or not sheet.is_file():
            raise ValueError(f"Image file not found: {sheet.name}")
        img = QImage(str(sheet))
        if img.isNull():
            raise ValueError(f"Cannot open image {sheet.name} (must be PNG)")
        img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        try:
            fw = int(man.get("frame_w") or img.width())
            fh = int(man.get("frame_h") or img.height())
        except (TypeError, ValueError) as e:
            raise ValueError("frame_w / frame_h must be numbers") from e
        if not (1 <= fw <= MAX_FRAME and 1 <= fh <= MAX_H):
            raise ValueError(f"Frame must be at most {MAX_FRAME} px wide and {MAX_H} px tall")
        if img.width() < fw or img.height() < fh:
            raise ValueError("Image is smaller than the frame size")
        order = man.get("poses") or list(POSES)
        if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
            raise ValueError("poses must be a list of pose names")
        frames: dict[str, list[QImage]] = {}
        for row, pose in enumerate(order):
            if (row + 1) * fh > img.height():
                break
            cells = [img.copy(c * fw, row * fh, fw, fh) for c in range(img.width() // fw)]
            cells = [c for c in cells if _has_pixels(c)]
            if cells:
                frames[pose] = cells
        if "sit" not in frames:
            raise ValueError("No sit pose found (the first row of the image must contain art)")
        try:
            scale = int(man.get("scale") or max(1, round(64 / fw)))
        except (TypeError, ValueError) as e:
            raise ValueError("scale must be an integer") from e
        scale = max(1, min(scale, 8, MAX_H // fh, 400 // fw))
        chest = man.get("chest")
        if chest is not None:
            try:
                chest = tuple(int(v) for v in chest)
                if len(chest) != 4:
                    raise ValueError
            except (TypeError, ValueError) as e:
                raise ValueError("chest must be [x, y, width, height]") from e
        return cls(sid, str(man.get("name") or folder.name), frames, fw, fh, scale, chest)

    def scale(self, family: str) -> int:
        return self._scale

    def width(self, family: str) -> int:
        return self.fw * self._scale

    def render(self, pose, tick, family, flip, mini=False):
        p = pose
        while p not in self.frames:
            p = FALLBACK.get(p, "sit")
        cells = self.frames[p]
        idx = (tick // (2 if pose == "run" else 3)) % len(cells)
        scale = max(1, self._scale // 2) if mini else self._scale
        key = (p, idx, scale, flip)
        pm = self._cache.get(key)
        if pm is None:
            img = cells[idx].scaled(self.fw * scale, self.fh * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
            pm = self._cache[key] = QPixmap.fromImage(img.mirrored(True, False) if flip else img)
        bob = YOFF.get(pose)
        if bob:
            y = bob[tick % 4]
        elif pose in ("walk", "run") and len(cells) == 1:      # static art still hops while moving
            y = (tick // 2) % 2
        else:
            y = 0
        return pm, y * scale

    def tag_rect(self, pose, family, flip):
        if not self.chest:
            return None
        x, y, w, h = self.chest
        s = self._scale
        return QRect(((self.fw - x - w) if flip else x) * s, y * s, w * s, h * s)


def _has_pixels(img: QImage) -> bool:
    """Any non-transparent pixel? (img is ARGB32_Premultiplied: alpha is every 4th byte)"""
    return any(bytes(img.constBits())[3::4])


# ---- registry ------------------------------------------------------------
def builtins() -> list[Skin]:
    return [BuiltinSkin("cat", "Cat", "cat"), BuiltinSkin("bunny", "Bunny", "bunny")]


_cache: tuple | None = None      # (signature, skins, errors)


def _signature() -> tuple:
    sig = []
    for d in sorted(p for p in skins_dir().iterdir() if p.is_dir()):
        sig.append((d.name, tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(d.iterdir())
                                  if f.is_file())))
    return tuple(sig)


def discover() -> tuple[dict[str, Skin], list[str]]:
    """(id -> Skin, error messages for skin folders that failed to load).
    Cached: folders are re-read only when something inside the skins folder changed (the menu calls this on every open)."""
    global _cache
    sig = _signature()
    if _cache is None or _cache[0] != sig:
        out: dict[str, Skin] = {s.id: s for s in builtins()}
        errors: list[str] = []
        for d in sorted(p for p in skins_dir().iterdir() if p.is_dir()):
            try:
                out[f"u:{d.name}"] = SheetSkin.load(d, f"u:{d.name}")
            except ValueError as e:
                errors.append(f"{d.name}: {e}")
        _cache = (sig, out, errors)
    return dict(_cache[1]), list(_cache[2])


def _unique_dir(name: str) -> Path:
    base = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_") or "skin"
    d, n = skins_dir() / base, 2
    while d.exists():
        d, n = skins_dir() / f"{base}_{n}", n + 1
    return d


def import_skin(src: Path) -> tuple[str | None, str]:
    """Import a .png sprite / .zip / skin.json (+sheet) into the skins folder. -> (skin id, "") or (None, error)."""
    src = Path(src)
    dst = _unique_dir(src.parent.name if src.name.lower() == "skin.json" else src.stem)
    try:
        dst.mkdir(parents=True)
        ext = src.suffix.lower()
        if ext == ".png":
            img = QImage(str(src))
            if img.isNull():
                raise ValueError("Cannot open image")
            shutil.copy2(src, dst / "sheet.png")
            (dst / "skin.json").write_text(json.dumps(
                {"name": src.stem, "frame_w": img.width(), "frame_h": img.height()}, ensure_ascii=False, indent=2),
                encoding="utf-8")
        elif ext == ".zip":
            _extract_zip(src, dst)
        elif src.name.lower() == "skin.json":
            man = json.loads(src.read_text(encoding="utf-8"))
            sheet = Path(str(man.get("sheet") or "sheet.png")).name
            shutil.copy2(src, dst / "skin.json")
            shutil.copy2(src.parent / sheet, dst / sheet)
        else:
            raise ValueError("Only .png, .zip or skin.json supported")
        sk = SheetSkin.load(dst, f"u:{dst.name}")
        return sk.id, ""
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        shutil.rmtree(dst, ignore_errors=True)
        return None, str(e)


def _extract_zip(zpath: Path, dst: Path) -> None:
    with zipfile.ZipFile(zpath) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_ZIP:
            raise ValueError("Zip file too large")
        files = [i for i in z.infolist() if not i.is_dir() and ".." not in i.filename]   # also blocks zip-slip
        names = [i.filename.replace("\\", "/") for i in files]
        # skin may sit at the zip root or inside a single top-level folder
        prefix = ""
        if not any(n in ("skin.json", "sheet.png") for n in names):
            tops = {n.split("/", 1)[0] for n in names if "/" in n}
            if len(tops) == 1:
                prefix = tops.pop() + "/"
        for info, n in zip(files, names):
            name = n[len(prefix):]
            if not n.startswith(prefix) or "/" in name:
                continue                                  # flat files only
            # allowlist + reject drive letters / NTFS streams ("C:x", "a.png:ads") / odd names
            if ":" in name or Path(name).name != name or not (name == "skin.json" or name.lower().endswith(".png")):
                continue
            target = (dst / name).resolve()
            if target.parent != dst.resolve():
                continue
            target.write_bytes(z.read(info))
