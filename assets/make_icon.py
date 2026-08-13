"""Build multiverse.ico from the official WV logo PNG."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "multiverse_logo.png"
OUT = ROOT / "multiverse.ico"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing logo source: {SRC}")

    base = Image.open(SRC).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    imgs = [base.resize((s, s), Image.Resampling.LANCZOS) for s, _ in sizes]
    imgs[0].save(OUT, format="ICO", sizes=sizes, append_images=imgs[1:])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
