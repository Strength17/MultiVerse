"""Generate multiverse.ico — gold M + AV on dark background."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "multiverse.ico"
BG = (14, 15, 18)
GOLD = (201, 168, 106)
WHITE = (236, 238, 241)


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=size // 6,
                           outline=GOLD + (200,), width=max(2, size // 64))
    try:
        import os
        win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        font_m = ImageFont.truetype(str(win / "georgiab.ttf"), int(size * 0.42))
        font_av = ImageFont.truetype(str(win / "segoeui.ttf"), int(size * 0.16))
    except Exception:
        font_m = ImageFont.load_default()
        font_av = font_m
    draw.text((size * 0.28, size * 0.18), "M", font=font_m, fill=GOLD + (255,))
    draw.text((size * 0.22, size * 0.58), "AV", font=font_av, fill=WHITE + (255,))
    return img


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    imgs = [render(s) for s, _ in sizes]
    imgs[0].save(OUT, format="ICO", sizes=sizes, append_images=imgs[1:])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
