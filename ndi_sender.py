"""
ndi_sender.py

Broadcasts the currently-displayed verse as a live NDI video source, so
vMix (or any other NDI receiver) can add MultiVerse as a normal input --
no capture window, no third-party screen-grab tool.

Design principles this follows (per the "no hardcoding, independent
failure" requirement):

  * Every visual/network setting (resolution, fps, font, colors, sender
    name) comes from NDIConfig (app_config.py / config.ini [ndi]) --
    nothing here is a hardcoded literal.
  * This module is fully independent of the detection pipeline. It only
    exposes update()/clear()/start()/stop() -- server.py calls those and
    never reaches into this module's internals. Swapping the renderer or
    the NDI library later only touches this file.
  * cyndilib (the NDI SDK wrapper) and the NDI Runtime DLL are optional
    at import time AND at runtime. If either is missing, start() logs
    ONE clear warning and every subsequent call becomes a no-op. A
    missing NDI install can never crash transcription, detection, or the
    WebSocket UI.
  * NDI expects a continuously live stream, not a single push -- a
    background thread re-sends the current frame at the configured fps
    so receivers never show it as frozen/stale, decoupled from how often
    verses actually change.
"""

from __future__ import annotations

import logging
import threading
import time

from app_config import NDIConfig

logger = logging.getLogger("multiverse.ndi")


class NDISender:
    def __init__(self, config: NDIConfig):
        self.config = config
        self._available = False
        self._ndi_send = None
        self._video_frame = None
        self._sender = None
        self._lock = threading.Lock()
        self._frame_bytes = None          # current RGBA numpy buffer to resend
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._warned = False
        self._font = None
        self._ref_font = None

    # ------------------------------------------------------------------
    def start(self):
        """Best-effort startup. Safe to call even when disabled/unavailable --
        every subsequent update()/clear() call just becomes a no-op."""
        if not self.config.enabled:
            logger.info("NDI output disabled in config.ini ([ndi] enabled = false)")
            return

        try:
            import numpy as np  # noqa: F401  (fail fast here if missing too)
            from cyndilib.wrapper.ndi_structs import FourCC
            from cyndilib.video_frame import VideoSendFrame
            from cyndilib.sender import Sender
        except ImportError as e:
            self._warn_once(
                "NDI output unavailable — 'cyndilib' (or a dependency) isn't installed. "
                "Run: pip install cyndilib pillow --break-system-packages  "
                f"({e}). The rest of MultiVerse is unaffected."
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
            # Most common cause: cyndilib imported fine (pure Python/Cython
            # wheel installed) but the actual NDI Runtime DLL/shared library
            # isn't present on this machine.
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

    # ------------------------------------------------------------------
    def update(self, reference: str, text: str, secondary_text: str | None = None):
        """Render a new verse-card frame and start broadcasting it. No-op
        (returns immediately) if NDI isn't available."""
        if not self._available:
            return
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

    def _load_fonts(self):
        from PIL import ImageFont
        try:
            if self.config.font_path:
                self._font = ImageFont.truetype(self.config.font_path, self.config.font_size)
                self._ref_font = ImageFont.truetype(self.config.font_path, self.config.reference_font_size)
            else:
                raise OSError("no font_path configured")
        except Exception:
            # Falls back to Pillow's built-in bitmap font -- always
            # available, so a missing/misconfigured font_path never
            # prevents NDI from working, it just looks plainer.
            self._font = ImageFont.load_default(size=self.config.font_size)
            self._ref_font = ImageFont.load_default(size=self.config.reference_font_size)

    def _render_frame(self, reference: str | None, text: str | None,
                       secondary_text: str | None):
        import numpy as np
        from PIL import Image, ImageDraw

        cfg = self.config
        r, g, b = cfg.background_color
        img = Image.new("RGBA", (cfg.width, cfg.height), (r, g, b, cfg.background_alpha))
        draw = ImageDraw.Draw(img)

        if text:
            tr, tg, tb = cfg.text_color
            max_width = cfg.width - 2 * cfg.margin

            ref_lines = [reference] if reference else []
            body_lines = _wrap_text(draw, text, self._font, max_width)
            secondary_lines = _wrap_text(draw, secondary_text, self._font, max_width) if secondary_text else []

            line_gap = int(cfg.font_size * 0.35)
            ref_h = cfg.reference_font_size + line_gap if ref_lines else 0
            body_h = len(body_lines) * (cfg.font_size + line_gap)
            sec_gap = int(cfg.font_size * 0.5) if secondary_lines else 0
            sec_h = len(secondary_lines) * (int(cfg.font_size * 0.85) + line_gap)
            total_h = ref_h + body_h + sec_gap + sec_h

            y = max(cfg.margin, (cfg.height - total_h) // 2)

            if ref_lines:
                draw.text((cfg.margin, y), ref_lines[0], font=self._ref_font, fill=(tr, tg, tb, 255))
                y += ref_h

            for line in body_lines:
                draw.text((cfg.margin, y), line, font=self._font, fill=(tr, tg, tb, 255))
                y += cfg.font_size + line_gap

            if secondary_lines:
                y += sec_gap
                sec_font = self._font  # same face, drawn a touch smaller via wrap width only
                for line in secondary_lines:
                    draw.text((cfg.margin, y), line, font=sec_font, fill=(tr, tg, tb, 200))
                    y += int(cfg.font_size * 0.85) + line_gap

        return np.asarray(img, dtype=np.uint8)

    def _resend_loop(self):
        """NDI wants a continuous stream even when the frame content hasn't
        changed. Runs independently of how often update() is called."""
        interval = 1.0 / max(self.config.fps, 0.1)
        # Start with a blank frame so the source is live immediately even
        # before the first verse triggers.
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
