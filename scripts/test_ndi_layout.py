"""Smoke-test NDI frame rendering (no sender required)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app_config import load_config
from ndi_sender import NDISender
from verse_display import DisplaySettings


def main():
    cfg = load_config()
    sender = NDISender(cfg.ndi)
    sender._load_fonts()
    sender.set_backgrounds_dir(Path("data/backgrounds"))
    sender.set_display(DisplaySettings())

    cases = [
        ("John 3:16", "For God so loved the world.", None, "short_single"),
        ("John 3:16", "For God so loved the world, that he gave his only begotten Son.", None, "medium_single"),
        (
            "John 3:16",
            "For God so loved the world, that he gave his only begotten Son.",
            "[French] Car Dieu a tant aimé le monde qu'il a donné son Fils unique.",
            "dual_medium",
        ),
        (
            "Psalm 119:105",
            "Thy word is a lamp unto my feet, and a light unto my path. "
            "The entrance of thy words giveth light; it giveth understanding unto the simple.",
            "[French] Ta parole est une lampe à mes pieds, et une lumière sur mon sentier.",
            "dual_long",
        ),
    ]
    out = Path("logs")
    out.mkdir(exist_ok=True)
    for ref, text, sec, name in cases:
        frame = sender._render_frame(ref, text, sec)
        from PIL import Image
        img = Image.fromarray(frame, "RGBA")
        path = out / f"ndi_test_{name}.png"
        img.save(path)
        print("Wrote", path, frame.shape)


if __name__ == "__main__":
    main()
