"""Generate packaging/buddy.ico from the built-in cat sprite (run by build.ps1)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter  # noqa: E402

app = QGuiApplication([])
from pixel_buddy import skins  # noqa: E402

pm, _ = skins.builtins()[0].render("sit", 2, "sonnet", False)
pm = pm.scaled(pm.width() * 4, pm.height() * 4)            # 256 x 192, nearest-neighbour look is kept by integer scale
img = QImage(256, 256, QImage.Format_ARGB32)
img.fill(QColor(0, 0, 0, 0))
p = QPainter(img)
p.drawPixmap((256 - pm.width()) // 2, 256 - pm.height() - 24, pm)
p.end()
out = ROOT / "packaging" / "buddy.ico"
assert img.save(str(out)), "cannot write ico (Qt ico plugin missing?)"
print("wrote", out)
