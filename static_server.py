"""Tiny HTTP server for the desktop UI and user background images."""
from __future__ import annotations

import logging
import mimetypes
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger("windowverse.static")
HTTP_PORT = 8766


class _Handler(SimpleHTTPRequestHandler):
    ui_root: Path = Path(".")
    backgrounds_root: Path = Path(".")

    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    def do_GET(self):
        from urllib.parse import unquote
        path = unquote(self.path.split("?", 1)[0])
        # Ensure proper path handling for absolute-like paths
        if path.startswith("/backgrounds/"):
            rel = path[len("/backgrounds/"):]
            # Normalize and combine with the actual backgrounds root
            target = (_Handler.backgrounds_root / rel.lstrip("/")).resolve()
            logger.info(f"Static request: path={path} -> rel={rel} -> target={target} (exists={target.exists()})")
            
            # Case-insensitive startswith comparison for Windows
            target_str = str(target).lower()
            root_str = str(_Handler.backgrounds_root.resolve()).lower()
            if not target_str.startswith(root_str):
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
        
        # Default behavior for other paths (UI files)
        super().do_GET()
        if path in ("/", "/ui", "/ui/"):
            path = "/ui/index.html"
        if path.startswith("/ui/"):
            rel = path[len("/ui/"):]
            target = (_Handler.ui_root / rel).resolve()
            
            # Case-insensitive startswith comparison for Windows
            target_str = str(target).lower()
            root_str = str(_Handler.ui_root.resolve()).lower()
            if not target_str.startswith(root_str):
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
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="windowverse-http")
    thread.start()
    logger.info("Static UI server at http://127.0.0.1:%d/ui/index.html", port)
    return server
