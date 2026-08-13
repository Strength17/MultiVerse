"""
Shared verse display layout — used by NDI output and mirrored in the UI via
broadcast_state. Handles dynamic font scaling for short/long and single/dual text.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bible_books import french_book_name

logger = logging.getLogger("windowverse.display")

USER_DISPLAY_FILE = "display_user.json"

PRIMARY_VERSION_LABEL = "[NKJV]"
SECONDARY_VERSION_LABEL = "[LSG]"


def bilingual_reference(book: str, chapter: int, verse: int, book_french: str | None = None) -> str:
    """French book • English book chapter:verse — e.g. Romains • Romans 8:1"""
    fr = book_french or french_book_name(book)
    return f"{fr} • {book} {chapter}:{verse}"


def estimate_wrapped_lines(text: str, chars_per_line: int) -> int:
    if not text or not text.strip():
        return 0
    words = text.split()
    lines = 1
    current = 0
    for word in words:
        wlen = len(word)
        if current and current + 1 + wlen > chars_per_line:
            lines += 1
            current = wlen
        elif current:
            current += 1 + wlen
        else:
            current = wlen
    return max(1, lines)


@dataclass
class ScreenLayout:
    ref_px: int
    body_px: int
    version_px: int
    block_gap: int
    line_gap: int
    pad_v: int
    pad_h: int


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
                "secondary": (20, 20, 24),
                "separator": (200, 200, 205),
            }
        return {
            "bg": (0, 0, 0),
            "bg_alpha": 255,
            "text": (245, 242, 234),
            "reference": (201, 168, 106),
            "secondary": (245, 242, 234),
            "separator": (35, 36, 41),
        }

    def to_ui_dict(self) -> dict:
        return asdict(self)


def compute_screen_layout(
    primary_lines: int,
    secondary_lines: int,
    canvas_w: int,
    canvas_h: int,
    text_scale: float = 1.0,
    ref_scale: float = 1.0,
) -> ScreenLayout:
    """Scale fonts to fill vertical space with even gaps between blocks."""
    has_sec = secondary_lines > 0
    pad_v = max(28, int(canvas_h * 0.045))
    pad_h = max(36, int(canvas_w * 0.045))
    avail_h = max(120, canvas_h - 2 * pad_v)

    body_px = max(28, int(58 * text_scale))

    def measure(px: int) -> tuple[int, ScreenLayout]:
        version_px = max(16, int(px * 0.46))
        ref_px = max(20, int(px * 0.58 * ref_scale))
        block_gap = max(12, int(px * 0.48))
        line_gap = max(6, int(px * 0.38))
        version_block = version_px + int(px * 0.2)
        primary_h = primary_lines * px + max(0, primary_lines - 1) * line_gap + version_block
        secondary_h = (
            secondary_lines * px + max(0, secondary_lines - 1) * line_gap + version_block
            if has_sec else 0
        )
        ref_block = ref_px + block_gap
        between = block_gap if has_sec else 0
        total = ref_block + primary_h + between + secondary_h
        layout = ScreenLayout(ref_px, px, version_px, block_gap, line_gap, pad_v, pad_h)
        return total, layout

    for _ in range(32):
        total, layout = measure(body_px)
        if total > avail_h:
            body_px = max(22, int(body_px * 0.93))
        elif total < avail_h * 0.88:
            body_px = int(body_px * min(1.14, avail_h / max(total, 1)))
        else:
            break

    return layout


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
    """Legacy helper — returns (ref_px, primary_px, secondary_px)."""
    chars = max(24, int(canvas_w * 0.88 / (base_primary * 0.55)))
    p_lines = estimate_wrapped_lines(primary_text or "", chars)
    s_lines = estimate_wrapped_lines(secondary_text or "", chars) if secondary_text else 0
    layout = compute_screen_layout(p_lines, s_lines, canvas_w, canvas_h, text_scale, ref_scale)
    return layout.ref_px, layout.body_px, layout.body_px


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
