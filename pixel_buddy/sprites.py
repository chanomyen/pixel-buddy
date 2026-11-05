"""Pixel-art for Pixel Buddy.

Everything is defined in code (no image assets). This module is pure Python so it
can be previewed without Qt (see preview_sprites.py).

Sprite grid: 16 x 12 cells, each cell is one "art pixel". Characters map to colours
through palette(). '.' is transparent.
"""
from __future__ import annotations

from dataclasses import dataclass

W, H = 16, 12
ICON = 7  # icons are 7 x 7 cells

BLANK = "." * W


def _row(*parts: str) -> str:
    return "".join(parts)


# Rows 0-9 are shared by all poses; rows 10-11 are the legs (see LEGS).
BASE = [
    _row("...", "o", ".......", "o", "...."),           # 0 ear tips
    _row("..", "obo", ".....", "obo", "..."),           # 1 ears
    _row("..", "obb", "ooooo", "bbo", "..."),           # 2 top of head
    _row("..", "o", "bbbbbbbbb", "o", "..."),           # 3 head
    _row("..", "o", "bbebbbebb", "o", "..."),           # 4 eyes
    _row("..", "o", "bbbbpbbbb", "o", "..."),           # 5 nose
    _row("..", "o", "bbbbbbbbb", "o", "..."),           # 6
    _row("..", "o", "bblllllbb", "o", ".o."),           # 7 belly / tail tip
    _row("..", "o", "bblllllbb", "o", "bo."),           # 8 belly / tail
    _row("..", "o", "bbbbbbbbb", "o", "..."),           # 9
]
LEGS = {
    0: [_row("..", "obo", ".....", "obo", "..."), _row("..", "ooo", ".....", "ooo", "...")],
    1: [_row("...", "obo", "...", "obo", "...."), _row("...", "ooo", "...", "ooo", "....")],
}

ICONS = {
    "search": [".ggg...", "g...g..", "g...g..", "g...g..", ".gggk..", ".....k.", "......k"],
    "edit": ["....oo.", "...oyyo", "..oyyo.", ".oyyo..", ".opo...", "opo....", "oo....."],
    "bash": ["ggggggg", "gnkkkkg", "gknkkkg", "gkknkkg", "gknkkkg", "gnkkwwg", "ggggggg"],
    "web": [".uuuuu.", "uunuuuu", "unnnuuu", "uunnuun", "uuunnnu", "uuuunuu", ".uuuuu."],
    "agent": ["...y...", ".uuuuu.", ".uwuwu.", ".uuuuu.", ".uwwwu.", "..uuu..", ".u...u."],
    "tool": ["...g...", ".g.g.g.", "..ggg..", "ggg.ggg", "..ggg..", ".g.g.g.", "...g..."],
    "alert": [".yyyyy.", "yy...yy", ".....yy", "...yyy.", "...y...", ".......", "...y..."],
    "done": [".......", "......n", ".....nn", "n...nn.", "nn.nn..", ".nnn...", "..n...."],
    "error": ["...r...", "...r...", "...r...", "...r...", "...r...", ".......", "...r..."],
}

for _k, _g in ICONS.items():
    assert len(_g) == ICON and all(len(r) == ICON for r in _g), _k
assert all(len(r) == W for r in BASE), [len(r) for r in BASE]
assert all(len(r) == W for v in LEGS.values() for r in v)

# body colour, light (belly) colour per model family
FAMILY_COLORS = {
    "sonnet": ("#f0903c", "#ffd9a0"),
    "haiku": ("#6fd3b5", "#d6fff0"),
    "opus": ("#a98bf0", "#e6dcff"),
    "fable": ("#f2c14e", "#fff1c2"),
    "mythos": ("#f2c14e", "#fff1c2"),
    "unknown": ("#9aa0a6", "#e3e6e8"),
}
CROWNED = {"opus", "fable", "mythos"}


def palette(family: str) -> dict[str, str]:
    body, light = FAMILY_COLORS.get(family, FAMILY_COLORS["unknown"])
    return {
        "o": "#2b1d14", "b": body, "l": light, "e": "#1a1a1a", "p": "#ff8fa3",
        "y": "#ffd23f", "g": "#aab0b7", "u": "#4aa3ff", "n": "#46c28a",
        "r": "#ff5a5f", "k": "#1e1e1e", "w": "#ffffff",
    }


@dataclass(frozen=True)
class Frame:
    grid: tuple[str, ...]
    yoff: int          # vertical bounce, in art pixels
    key: tuple         # cache key (everything that changes the grid)


def _put(g: list[list[str]], x: int, y: int, c: str) -> None:
    if 0 <= y < H and 0 <= x < W:
        g[y][x] = c


def build(pose: str, tick: int, family: str = "sonnet") -> Frame:
    """pose: sit | walk | run | sleep | alert | happy | error"""
    legs = {"walk": (tick // 2) % 2, "run": tick % 2}.get(pose, 0)
    wag = (tick // 3) % 2 if pose != "sleep" else 0
    blink = pose == "sit" and tick % 48 in (0, 1)
    arm = (tick // 2) % 2 if pose == "alert" else -1
    crown = family in CROWNED

    base = [list(r) for r in BASE]
    dy = 0
    if pose == "sleep":
        # curled loaf: drop legs, shift everything down 2 rows, add a bottom outline
        g = [list(BLANK), list(BLANK)] + base[:9] + [list("..ooooooooooo...")]
        dy = 2
    else:
        g = base + [list(r) for r in LEGS[legs]]

    if wag:
        _put(g, 14, 7 + dy, ".")
        _put(g, 13, 9 + dy, "b")
        _put(g, 14, 9 + dy, "o")

    ey = 4 + dy  # eye row
    eyes = "open"
    if pose == "sleep":
        eyes = "line"
        for x in (4, 5, 6, 8, 9, 10):
            _put(g, x, ey, "e")
    elif pose == "happy":
        eyes = "happy"
        for x in (5, 9):
            _put(g, x, ey, "b")
        for x, y in ((4, ey), (5, ey - 1), (6, ey), (8, ey), (9, ey - 1), (10, ey)):
            _put(g, x, y, "e")
    elif pose == "error":
        eyes = "x"
        for x in (5, 9):
            _put(g, x, ey, "b")
        for cx in (5, 9):
            for ddx, ddy in ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)):
                _put(g, cx + ddx, ey + ddy, "e")
    elif blink:
        eyes = "blink"
        for x in (5, 9):
            _put(g, x, ey, "b")

    if arm >= 0:
        left = ({(1, 7): "o", (1, 6): "b", (1, 5): "o"} if arm == 0
                else {(1, 6): "o", (1, 5): "b", (0, 4): "o", (1, 4): "o"})
        for (x, y), c in left.items():
            _put(g, x, y, c)
            _put(g, W - 1 - x, y, c)

    if crown:
        for x, y in ((6, 0), (8, 0), (6, 1), (7, 1), (8, 1)):
            _put(g, x, y + dy, "y")

    yoff = 0
    if pose == "alert":
        yoff = (0, 1, 2, 1)[tick % 4]
    elif pose == "happy":
        yoff = (0, 2, 3, 2)[tick % 4]

    grid = tuple("".join(r) for r in g)
    return Frame(grid=grid, yoff=yoff, key=(pose, legs, wag, eyes, arm, crown))


def icon_for(state: str, kind: str) -> list[str] | None:
    if state == "alert":
        return ICONS["alert"]
    if state == "done":
        return ICONS["done"]
    if state == "error":
        return ICONS["error"]
    if state == "tool":
        return ICONS.get(kind, ICONS["tool"])
    return None
