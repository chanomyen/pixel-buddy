"""Render a contact sheet of every pose / model / icon to sprites_preview.png (needs Pillow)."""
from pixel_buddy import sprites
from PIL import Image, ImageDraw

S = 8
POSES = ["sit", "walk", "run", "sleep", "alert", "happy", "error"]
FAMILIES = ["sonnet", "haiku", "opus", "fable"]


def draw_grid(img, grid, pal, ox, oy, s=S):
    d = ImageDraw.Draw(img)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != "." and ch in pal:
                d.rectangle([ox + x * s, oy + y * s, ox + (x + 1) * s - 1, oy + (y + 1) * s - 1], fill=pal[ch])


def main(out="sprites_preview.png"):
    cw, ch = sprites.W * S + 16, sprites.H * S + 16
    iconrow = 7 * 5 + 16
    img = Image.new("RGB", (cw * len(POSES), ch * len(FAMILIES) + iconrow + 10), "#2b2d31")
    for r, fam in enumerate(FAMILIES):
        pal = sprites.palette(fam)
        for c, pose in enumerate(POSES):
            fr = sprites.build(pose, 1 if pose in ("walk", "run") else 4, fam)
            draw_grid(img, fr.grid, pal, c * cw + 8, r * ch + 8)
    pal = sprites.palette("sonnet")
    for i, (name, g) in enumerate(sprites.ICONS.items()):
        draw_grid(img, g, pal, i * (7 * 5 + 14) + 10, ch * len(FAMILIES) + 6, 5)
    img.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
