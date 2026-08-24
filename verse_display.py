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
    text_color: str = "#ffffff"            # hex color for text
    background_mode: str = "solid"         # solid | image
    background_image: str = ""             # filename under data/backgrounds/
    secondary_above: bool = False
    ndi_output_enabled: bool = True
    ref_position: str = "top"              # top | bottom
    vertical_position: str = "center"      # top | center | bottom
    block_gap_scale: float = 1.0           # multiplier on spacing between blocks
    line_gap_scale: float = 1.0            # multiplier on spacing between lines
    ref_color: str = "#2b9bff"             # hex color for reference

    def effective_colors(self) -> dict:
        def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
            h = hex_str.lstrip('#')
            if len(h) == 6:
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            return (255, 255, 255)

        custom_text = hex_to_rgb(self.text_color)
        custom_ref = hex_to_rgb(self.ref_color)

        if self.theme == "light":
            return {
                "bg": (255, 255, 255),
                "bg_alpha": 255,
                "text": custom_text if self.text_color != "#ffffff" else (20, 20, 24),
                "reference": custom_ref if self.ref_color != "#2b9bff" else (140, 100, 40),
                "secondary": custom_text if self.text_color != "#ffffff" else (20, 20, 24),
                "separator": (200, 200, 205),
            }
        return {
            "bg": (0, 0, 0),
            "bg_alpha": 255,
            "text": custom_text,
            "reference": custom_ref,
            "secondary": custom_text,
            "separator": (35, 36, 41),
        }

    def to_ui_dict(self) -> dict:
        return asdict(self)


def compute_screen_layout(
    primary_text: str,
    secondary_text: str | None = None,
    canvas_w: int = 1920,
    canvas_h: int = 1080,
    text_scale: float = 1.0,
    ref_scale: float = 1.0,
    primary_label: str = PRIMARY_VERSION_LABEL,
    secondary_label: str = SECONDARY_VERSION_LABEL,
    block_gap_scale: float = 1.0,
    line_gap_scale: float = 1.0,
) -> ScreenLayout:
    """Binary-search font size so short verses read large and long verses shrink to fit."""
    pad_v = max(24, int(canvas_h * 0.05))
    pad_h = max(32, int(canvas_w * 0.06))
    avail_h = max(100, canvas_h - 2 * pad_v)
    avail_w = max(200, int(canvas_w - 2 * pad_h))

    p_full = f"{primary_label} {primary_text}".strip() if primary_text else ""
    s_full = (
        f"{secondary_label} {secondary_text}".strip()
        if secondary_text else ""
    )

    body_px = max(22, int(min(76, canvas_h * 0.058) * text_scale))
    ref_px = body_px
    line_gap = 6
    block_gap = 10

    def block_height(n_lines: int, px: int, lg: int) -> int:
        if n_lines <= 0:
            return 0
        return n_lines * px + max(0, n_lines - 1) * lg

    for _ in range(52):
        chars_per_line = max(14, int(avail_w / max(8, body_px * 0.52)))
        ref_px = max(16, int(body_px * 0.62 * ref_scale))
        line_gap = max(4, int(body_px * 0.30 * line_gap_scale))
        block_gap = max(8, int(body_px * 0.42 * block_gap_scale))
        p_lines = estimate_wrapped_lines(p_full, chars_per_line)
        s_lines = estimate_wrapped_lines(s_full, chars_per_line) if s_full else 0
        total = ref_px + block_gap
        total += block_height(p_lines, body_px, line_gap)
        if s_lines:
            total += block_gap + block_height(s_lines, body_px, line_gap)
        if total > avail_h:
            body_px = max(16, int(body_px * 0.905))
        elif (
            total < avail_h * 0.86
            and body_px < int(min(84, canvas_h * 0.072) * text_scale)
        ):
            body_px = int(body_px * 1.055)
        else:
            break

    return ScreenLayout(
        ref_px, body_px, body_px, block_gap, line_gap, pad_v, pad_h,
    )


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
    layout = compute_screen_layout(
        primary_text or "",
        secondary_text,
        canvas_w,
        canvas_h,
        text_scale,
        ref_scale,
    )
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
