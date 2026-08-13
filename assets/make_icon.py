"""Generate windowverse.ico — WV monogram on dark glass background."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "windowverse.ico"
BG = (10, 12, 20)
ACCENT = (126, 184, 255)
SILVER = (200, 208, 220)


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=size // 6,
        outline=SILVER + (220,),
        width=max(2, size // 64),
    )
    try:
        import os
        win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        font_w = ImageFont.truetype(str(win / "georgiab.ttf"), int(size * 0.38))
        font_v = ImageFont.truetype(str(win / "georgiab.ttf"), int(size * 0.30))
    except Exception:
        font_w = ImageFont.load_default()
        font_v = font_w
    draw.text((size * 0.20, size * 0.22), "W", font=font_w, fill=ACCENT + (255,))
    draw.text((size * 0.48, size * 0.38), "V", font=font_v, fill=SILVER + (255,))
    return img


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    imgs = [render(s) for s, _ in sizes]
    imgs[0].save(OUT, format="ICO", sizes=sizes, append_images=imgs[1:])
    legacy = ROOT / "assets" / "multiverse.ico"
    imgs[0].save(legacy, format="ICO", sizes=sizes, append_images=imgs[1:])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
