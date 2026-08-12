"""
MultiVerse desktop entry point — single window (WebView2), embedded server, clean shutdown.
"""
from __future__ import annotations

import logging
import socket
import sys
import threading
import time

from paths import app_root, bootstrap_install, resource_root
from static_server import HTTP_PORT

PORT = 8765
logger = logging.getLogger("multiverse.desktop")


def _wait_for_port(host: str = "127.0.0.1", port: int = PORT, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def _run_server():
    import os
    os.chdir(app_root())
    bootstrap_install()
    (app_root() / "logs").mkdir(exist_ok=True)
    from server import main as server_main
    server_main()


def main():
    bootstrap_install()
    t = threading.Thread(target=_run_server, daemon=True, name="multiverse-server")
    t.start()
    if not _wait_for_port(port=PORT):
        print("Backend failed to start on port", PORT, file=sys.stderr)
        sys.exit(1)
    # HTTP static server starts inside server.run(); give it a moment
    time.sleep(0.5)

    import webview

    url = f"http://127.0.0.1:{HTTP_PORT}/ui/index.html"
    icon = resource_root() / "assets" / "multiverse.ico"
    if not icon.exists():
        icon = app_root() / "assets" / "multiverse.ico"

    window = webview.create_window(
        "MultiVerse — Live Service",
        url=url,
        width=1440,
        height=900,
        min_size=(1100, 700),
        background_color="#0e0f12",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
