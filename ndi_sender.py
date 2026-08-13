"""
ndi_sender.py

Broadcasts the currently-displayed verse as a live NDI video source, so
vMix (or any other NDI receiver) can add Window Verse as a normal input --
no capture window, no third-party screen-grab tool.

The frame layout mirrors the Live Output stage in ui/index.html exactly:
centered black canvas, gold reference, primary verse text, optional dashed
separator, optional italic secondary translation (above or below primary).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from app_config import NDIConfig
from verse_display import DisplaySettings, compute_screen_layout

logger = logging.getLogger("windowverse.ndi")


class NDISender:
    def __init__(self, config: NDIConfig):
        self.config = config
        self._available = False
        self._ndi_send = None
        self._video_frame = None
        self._sender = None
        self._lock = threading.Lock()
        self._frame_bytes = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._warned = False
        self._font = None
        self._font_bold = None
        self._ref_font = None
        self._sec_font = None
        self._sec_font_bold = None
        self._display = DisplaySettings()
        self._backgrounds_dir: Path | None = None

    # ------------------------------------------------------------------
    def start(self):
        """Best-effort startup. Safe to call even when disabled/unavailable --
        every subsequent update()/clear() call just becomes a no-op."""
        if not self.config.enabled:
            logger.info("NDI output disabled in config.ini ([ndi] enabled = false)")
            return

        try:
            import numpy as np  # noqa: F401
            from cyndilib.wrapper.ndi_structs import FourCC
            from cyndilib.video_frame import VideoSendFrame
            from cyndilib.sender import Sender
        except ImportError as e:
            self._warn_once(
                "NDI output unavailable — 'cyndilib' (or a dependency) isn't installed. "
                "Run: pip install cyndilib pillow --break-system-packages  "
                f"({e}). The rest of Window Verse is unaffected."
            )
            return

        try:
            from fractions import Fraction

            self._sender = Sender(self.config.sender_name)
            self._video_frame = VideoSendFrame()
            self._video_frame.set_resolution(self.config.width, self.config.height)
            self._video_frame.set_frame_rate(
                Fraction(int(round(self.config.fps)) or 1, 1)
            )
            self._video_frame.set_fourcc(FourCC.RGBA)
            self._sender.set_video_frame(self._video_frame)
            self._sender.open()
        except Exception as e:
            self._warn_once(
                "NDI output unavailable — could not open an NDI sender. This "
                "usually means the NDI Runtime isn't installed on this machine "
                f"(get it free from ndi.video). Detail: {e}"
            )
            self._sender = None
            return

        self._load_fonts()
        self._available = True
        self._send_buffer = bytearray(self._video_frame.get_data_size())
        self._send_view = memoryview(self._send_buffer)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._resend_loop, daemon=True)
        self._thread.start()
        logger.info(
            "NDI sender '%s' started (%dx%d @ %.1ffps)",
            self.config.sender_name, self.config.width, self.config.height, self.config.fps,
        )

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._sender is not None:
            try:
                self._sender.close()
            except Exception:
                logger.exception("Error closing NDI sender")
        self._available = False

    def set_backgrounds_dir(self, path: Path | None):
        self._backgrounds_dir = path

    def set_display(self, display: DisplaySettings):
        self._display = display

    # ------------------------------------------------------------------
    def update(self, reference: str, text: str, secondary_text: str | None = None,
               secondary_above: bool | None = None, display: DisplaySettings | None = None):
        """Render a new verse-card frame and start broadcasting it."""
        if not self._available:
            return
        if display is not None:
            self._display = display
        if secondary_above is not None:
            self._display.secondary_above = secondary_above
        try:
            frame = self._render_frame(reference, text, secondary_text)
        except Exception:
            logger.exception("NDI frame render failed — leaving last frame on air")
            return
        with self._lock:
            self._frame_bytes = frame

    def clear(self):
        """Blank the output (e.g. when going off-air)."""
        if not self._available:
            return
        try:
            frame = self._render_frame(None, None, None)
        except Exception:
            logger.exception("NDI clear-frame render failed")
            return
        with self._lock:
            self._frame_bytes = frame

    # ------------------------------------------------------------------
    def _warn_once(self, message: str):
        if not self._warned:
            logger.warning(message)
            self._warned = True

    def _resolve_font_path(self) -> str | None:
        if self.config.font_path and Path(self.config.font_path).exists():
            return self.config.font_path
        win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("Source Serif 4", "georgia", "times"):
            for ext in (".ttf", "bd.ttf", "i.ttf"):
                candidate = win / f"{name}{ext}"
                if candidate.exists():
                    return str(candidate)
        for name in ("georgia.ttf", "times.ttf"):
            candidate = win / name
            if candidate.exists():
                return str(candidate)
        return None

    def _load_fonts(self):
        from PIL import ImageFont
        cfg = self.config
        path = self._resolve_font_path()
        italic_path = None
        if path:
            stem = Path(path)
            for candidate in (stem.parent / f"{stem.stem}i{stem.suffix}",
                              stem.parent / "georgiai.ttf"):
                if candidate.exists():
                    italic_path = str(candidate)
                    break
        try:
            if path:
                self._font = ImageFont.truetype(path, cfg.font_size)
                self._ref_font = ImageFont.truetype(path, cfg.reference_font_size)
                self._sec_font = ImageFont.truetype(
                    italic_path or path, cfg.secondary_font_size)
            else:
                raise OSError("no serif font found")
        except Exception:
            self._font = ImageFont.load_default(size=cfg.font_size)
            self._ref_font = ImageFont.load_default(size=cfg.reference_font_size)
            self._sec_font = ImageFont.load_default(size=cfg.secondary_font_size)

    def _render_frame(self, reference: str | None, text: str | None,
                       secondary_text: str | None):
        import numpy as np
        from PIL import Image, ImageDraw

        cfg = self.config
        disp = self._display
        colors = disp.effective_colors()
        br, bg, bb = colors["bg"]
        img = Image.new("RGBA", (cfg.width, cfg.height), (br, bg, bb, colors["bg_alpha"]))
        draw = ImageDraw.Draw(img)

        if disp.background_mode == "image" and disp.background_image and self._backgrounds_dir:
            bg_path = self._backgrounds_dir / disp.background_image
            if bg_path.exists():
                try:
                    bg = Image.open(bg_path).convert("RGBA").resize((cfg.width, cfg.height))
                    img = Image.alpha_composite(bg, img)
                    draw = ImageDraw.Draw(img)
                except Exception:
                    logger.exception("Background image load failed: %s", bg_path)

        if not text:
            return np.asarray(img, dtype=np.uint8)

        from verse_display import (
            PRIMARY_VERSION_LABEL, SECONDARY_VERSION_LABEL, compute_screen_layout,
        )

        max_width = int(cfg.width * (1 - 0.09))
        x_center = cfg.width // 2
        secondary_above = disp.secondary_above

        p_full = f"{PRIMARY_VERSION_LABEL} {text}".strip()
        s_full = (
            f"{SECONDARY_VERSION_LABEL} {secondary_text}".strip()
            if secondary_text else ""
        )
        layout = compute_screen_layout(
            text, secondary_text,
            cfg.width, cfg.height, disp.text_scale, disp.ref_scale,
            PRIMARY_VERSION_LABEL, SECONDARY_VERSION_LABEL,
        )
        body_px = layout.body_px
        self._ensure_fonts(body_px, layout.ref_px, body_px, disp)
        primary_lines = _wrap_text(draw, p_full, self._font, max_width)
        secondary_lines = (
            _wrap_text(draw, s_full, self._font, max_width) if s_full else []
        )

        ref_px = layout.ref_px
        primary_px = layout.body_px
        sec_px = layout.body_px
        block_gap = layout.block_gap
        line_gap = layout.line_gap
        pad_v = layout.pad_v

        def block_height(lines, font_size):
            if not lines:
                return 0
            return len(lines) * font_size + max(0, len(lines) - 1) * line_gap

        primary_h = block_height(primary_lines, primary_px)
        secondary_h = block_height(secondary_lines, sec_px) if secondary_lines else 0
        ref_block = ref_px + block_gap if reference else 0
        between = block_gap if secondary_lines else 0
        total_h = ref_block + primary_h + between + secondary_h
        y = pad_v + max(0, (cfg.height - 2 * pad_v - total_h) // 2)

        rr, rg, rb = colors["reference"]
        tr, tg, tb = colors["text"]
        sr, sg, sb = colors["secondary"]

        if disp.show_border:
            pad = 24
            draw.rectangle(
                [pad, pad, cfg.width - pad, cfg.height - pad],
                outline=(rr, rg, rb, 180), width=3,
            )

        if reference:
            _draw_centered_line(draw, reference, self._ref_font_bold, x_center, y, (rr, rg, rb, 255))
            y += ref_px + block_gap

        def draw_primary():
            nonlocal y
            font = self._font_bold if disp.primary_bold else self._font
            for line in primary_lines:
                _draw_centered_line(draw, line, font, x_center, y, (tr, tg, tb, 255))
                y += primary_px + line_gap

        def draw_secondary():
            nonlocal y
            font = self._sec_font if disp.secondary_italic else self._font
            for line in secondary_lines:
                _draw_centered_line(draw, line, font, x_center, y, (sr, sg, sb, 255))
                y += sec_px + line_gap

        if secondary_lines and secondary_above:
            draw_secondary()
            y += block_gap
            draw_primary()
        else:
            draw_primary()
            if secondary_lines:
                y += block_gap
                draw_secondary()

        return np.asarray(img, dtype=np.uint8)

    def _ensure_fonts(self, primary_px: int, ref_px: int, sec_px: int, disp: DisplaySettings):
        from PIL import ImageFont
        path = self._resolve_font_path()
        sans = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf"
        if disp.font_family == "sans" and sans.exists():
            path = str(sans)
        italic_path = None
        if path:
            stem = Path(path)
            for candidate in (stem.parent / f"{stem.stem}i{stem.suffix}",
                              stem.parent / "segoei.ttf", stem.parent / "georgiai.ttf"):
                if candidate.exists():
                    italic_path = str(candidate)
                    break
        try:
            if path:
                bold_path = path
                stem = Path(path)
                for candidate in (stem.parent / f"{stem.stem}bd{stem.suffix}",
                                  stem.parent / "georgiab.ttf",
                                  stem.parent / "arialbd.ttf"):
                    if candidate.exists():
                        bold_path = str(candidate)
                        break
                self._font = ImageFont.truetype(path, primary_px)
                self._font_bold = ImageFont.truetype(bold_path, primary_px)
                self._ref_font = ImageFont.truetype(path, ref_px)
                self._ref_font_bold = ImageFont.truetype(bold_path, ref_px)
                sec_font_path = italic_path or path
                if disp.secondary_italic and italic_path:
                    sec_font_path = italic_path
                elif not disp.secondary_italic:
                    sec_font_path = path
                self._sec_font = ImageFont.truetype(sec_font_path, sec_px)
            else:
                raise OSError("no font")
        except Exception:
            self._font = ImageFont.load_default(size=primary_px)
            self._font_bold = self._font
            self._ref_font = ImageFont.load_default(size=ref_px)
            self._ref_font_bold = self._ref_font
            self._sec_font = ImageFont.load_default(size=sec_px)

    def _resend_loop(self):
        interval = 1.0 / max(self.config.fps, 0.1)
        with self._lock:
            if self._frame_bytes is None:
                try:
                    self._frame_bytes = self._render_frame(None, None, None)
                except Exception:
                    logger.exception("Initial blank NDI frame failed")

        while not self._stop_event.is_set():
            start = time.monotonic()
            with self._lock:
                frame = self._frame_bytes
            if frame is not None and self._sender is not None:
                try:
                    payload = frame.tobytes()
                    if len(payload) != len(self._send_buffer):
                        self._send_buffer = bytearray(len(payload))
                        self._send_view = memoryview(self._send_buffer)
                    self._send_buffer[:] = payload
                    self._sender.write_video_async(self._send_view)
                except Exception:
                    logger.exception("NDI frame send failed — will retry next tick")
            elapsed = time.monotonic() - start
            self._stop_event.wait(max(0.0, interval - elapsed))


def _draw_centered_line(draw, text: str, font, x_center: int, y: int, fill):
    w = draw.textlength(text, font=font)
    draw.text((x_center - w / 2, y), text, font=font, fill=fill)


def _draw_dashed_line(draw, y: int, x0: int, x1: int, color):
    dash, gap = 10, 8
    x = x0
    while x < x1:
        draw.line([(x, y), (min(x + dash, x1), y)], fill=color, width=1)
        x += dash + gap


def _wrap_text(draw, text: str | None, font, max_width: int) -> list[str]:
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        w = draw.textlength(candidate, font=font)
        if w <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
