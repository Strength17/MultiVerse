"""Tiny HTTP server for the desktop UI and user background images."""
from __future__ import annotations

import logging
import mimetypes
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger("multiverse.static")
HTTP_PORT = 8766


class _Handler(SimpleHTTPRequestHandler):
    ui_root: Path = Path(".")
    backgrounds_root: Path = Path(".")

    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/backgrounds/"):
            rel = path[len("/backgrounds/"):]
            target = (_Handler.backgrounds_root / rel).resolve()
            if not str(target).startswith(str(_Handler.backgrounds_root.resolve())):
                self.send_error(403)
                return
            if not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path in ("/", "/ui", "/ui/"):
            path = "/ui/index.html"
        if path.startswith("/ui/"):
            rel = path[len("/ui/"):]
            target = (_Handler.ui_root / rel).resolve()
            if not str(target).startswith(str(_Handler.ui_root.resolve())):
                self.send_error(403)
                return
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)


def start_static_server(ui_root: Path, backgrounds_root: Path, port: int = HTTP_PORT) -> ThreadingHTTPServer:
    _Handler.ui_root = ui_root.resolve()
    _Handler.backgrounds_root = backgrounds_root.resolve()
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="multiverse-http")
    thread.start()
    logger.info("Static UI server at http://127.0.0.1:%d/ui/index.html", port)
    return server
