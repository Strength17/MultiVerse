"""
Shared verse display layout — used by NDI output and mirrored in the UI via
broadcast_state. Handles dynamic font scaling for short/long and single/dual text.
"""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger("multiverse.display")

USER_DISPLAY_FILE = "display_user.json"


@dataclass
class DisplaySettings:
    theme: str = "dark"                    # dark | light
    font_family: str = "serif"             # serif | sans
    primary_bold: bool = False
    primary_italic: bool = False
    secondary_italic: bool = True
    show_border: bool = False
    ref_scale: float = 1.0                 # multiplier on reference size
    text_scale: float = 1.0                # multiplier on body sizes
    background_mode: str = "solid"         # solid | image
    background_image: str = ""             # filename under data/backgrounds/
    secondary_above: bool = False
    ndi_output_enabled: bool = True

    def effective_colors(self) -> dict:
        if self.theme == "light":
            return {
                "bg": (255, 255, 255),
                "bg_alpha": 255,
                "text": (20, 20, 24),
                "reference": (140, 100, 40),
                "secondary": (80, 82, 90),
                "separator": (200, 200, 205),
            }
        return {
            "bg": (0, 0, 0),
            "bg_alpha": 255,
            "text": (245, 242, 234),
            "reference": (201, 168, 106),
            "secondary": (148, 151, 163),
            "separator": (35, 36, 41),
        }

    def to_ui_dict(self) -> dict:
        return asdict(self)


def compute_dynamic_sizes(
    primary_text: str,
    secondary_text: str | None,
    base_ref: int = 44,
    base_primary: int = 56,
    base_secondary: int = 46,
    text_scale: float = 1.0,
    ref_scale: float = 1.0,
    canvas_w: int = 1920,
    canvas_h: int = 1080,
) -> tuple[int, int, int]:
    """Return (ref_px, primary_px, secondary_px) scaled to fit content."""
    has_sec = bool(secondary_text and secondary_text.strip())
    total_chars = len(primary_text or "") + (len(secondary_text or "") if has_sec else 0)
    line_estimate = max(1, total_chars // 42 + (2 if has_sec else 0))

    # Single language + short text → larger
    scale = text_scale
    if not has_sec:
        if total_chars < 90:
            scale *= 1.35
        elif total_chars < 150:
            scale *= 1.15
    else:
        if total_chars < 120:
            scale *= 1.2
        elif total_chars > 280:
            scale *= 0.82

    if line_estimate > 6:
        scale *= max(0.55, 6 / line_estimate)
    elif line_estimate > 4:
        scale *= 0.88

    ref_px = max(28, int(base_ref * ref_scale * min(1.2, scale + 0.05)))
    primary_px = max(32, int(base_primary * scale))
    secondary_px = max(28, int(base_secondary * scale * 0.92))
    return ref_px, primary_px, secondary_px


def load_user_display(path: Path) -> DisplaySettings:
    if not path.exists():
        return DisplaySettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        known = set(DisplaySettings.__dataclass_fields__)
        filtered = {k: v for k, v in data.items() if k in known}
        return DisplaySettings(**filtered)
    except Exception:
        logger.exception("Failed to load %s — using defaults", path)
        return DisplaySettings()


def save_user_display(path: Path, settings: DisplaySettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_ui_dict(), indent=2), encoding="utf-8")


def list_background_images(backgrounds_dir: Path) -> list[str]:
    if not backgrounds_dir.exists():
        return []
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    return sorted(
        p.name for p in backgrounds_dir.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )
