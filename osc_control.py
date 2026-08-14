"""
osc_control.py

OSC (Open Sound Control) remote listener for broadcast integration --
mirrors Pewbeam's documented address scheme so existing OSC-based
broadcast controllers/mixing consoles built against Pewbeam's protocol
work against this backend with no changes.

Pewbeam listens on UDP port 8000 with these documented addresses:
    /pew/next            -- next verse
    /pew/prev            -- previous verse
    /pew/show            -- show verse
    /pew/hide            -- hide verse
    /pew/theme   string  -- set theme by name
    /pew/opacity float   -- set verse opacity (0-1)
    /pew/confidence float -- set detection confidence threshold (0-1)
    /pew/on_air  bool    -- toggle on-air status
    /pew/mode    string  -- set broadcast mode

Pewbeam's own docs note next/prev/show/hide are "still being wired
through" on their end at time of writing -- this implementation wires
all of them all the way through to the queue and on-air state.

Requires: pip install python-osc --break-system-packages
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("windowverse.osc_control")

OSC_PORT = 8000


class OSCController:
    """
    Wraps python-osc's async UDP server. Call `start()` once during
    server startup from within a running asyncio loop, passing a
    reference to the WindowVerseServer instance so OSC commands drive
    the same queue/display state as the WebSocket UI.
    """

    def __init__(self, mv_server, port: int = OSC_PORT):
        self.mv_server = mv_server
        self.port = port
        self._transport = None
        self._protocol = None

    async def start(self):
        try:
            from pythonosc.dispatcher import Dispatcher
            from pythonosc.osc_server import AsyncIOOSCUDPServer
        except ImportError:
            logger.warning(
                "python-osc not installed -- OSC remote control disabled. "
                "Install with: pip install python-osc --break-system-packages"
            )
            return

        dispatcher = Dispatcher()
        dispatcher.map("/pew/next", self._on_next)
        dispatcher.map("/pew/prev", self._on_prev)
        dispatcher.map("/pew/show", self._on_show)
        dispatcher.map("/pew/hide", self._on_hide)
        dispatcher.map("/pew/theme", self._on_theme)
        dispatcher.map("/pew/opacity", self._on_opacity)
        dispatcher.map("/pew/confidence", self._on_confidence)
        dispatcher.map("/pew/on_air", self._on_air)
        dispatcher.map("/pew/mode", self._on_mode)
        dispatcher.set_default_handler(self._on_unknown)

        loop = asyncio.get_running_loop()
        server = AsyncIOOSCUDPServer(("0.0.0.0", self.port), dispatcher, loop)
        self._transport, self._protocol = await server.create_serve_endpoint()
        logger.info("OSC listener active on UDP port %d (Pewbeam-compatible addresses)",
                    self.port)

    def stop(self):
        if self._transport:
            self._transport.close()

    def _on_next(self, address, *args):
        logger.info("OSC: next verse")
        self.mv_server.queue_advance(direction=1)

    def _on_prev(self, address, *args):
        logger.info("OSC: previous verse")
        self.mv_server.queue_advance(direction=-1)

    def _on_show(self, address, *args):
        logger.info("OSC: show verse")
        self.mv_server.set_on_air(True)

    def _on_hide(self, address, *args):
        logger.info("OSC: hide verse")
        self.mv_server.set_on_air(False)

    def _on_theme(self, address, theme_name=None, *args):
        logger.info("OSC: set theme -> %s", theme_name)
        self.mv_server.set_theme(theme_name)

    def _on_opacity(self, address, value=None, *args):
        logger.info("OSC: set opacity -> %s", value)
        self.mv_server.set_opacity(float(value) if value is not None else 1.0)

    def _on_confidence(self, address, value=None, *args):
        logger.info("OSC: set confidence threshold -> %s", value)
        if value is not None:
            self.mv_server.set_confidence_threshold(float(value))

    def _on_air(self, address, value=None, *args):
        logger.info("OSC: on_air -> %s", value)
        self.mv_server.set_on_air(bool(value))

    def _on_mode(self, address, mode_name=None, *args):
        logger.info("OSC: set broadcast mode -> %s", mode_name)
        self.mv_server.set_broadcast_mode(mode_name)

    def _on_unknown(self, address, *args):
        logger.debug("OSC: unrecognized address %s args=%s", address, args)
