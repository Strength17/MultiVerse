"""
WindowVerse desktop entry point — single window (WebView2), embedded server, clean shutdown.
"""
from __future__ import annotations

# Load torch before WebView2/WinRT native DLLs — avoids WinError 1114 on c10.dll in some sessions.
try:
    import torch  # noqa: F401
except OSError:
    torch = None  # type: ignore

import logging
import socket
import sys
import threading
import time

from paths import app_root, bootstrap_install, resource_root
from static_server import HTTP_PORT

PORT = 8765
logger = logging.getLogger("windowverse.desktop")


def _ensure_winrt_dependencies() -> None:
    """Install any missing WinRT speech packages before the UI opens."""
    import subprocess
    from winrt_pipeline import verify_winrt_dependencies, winrt_install_hint

    missing = verify_winrt_dependencies()
    if not missing:
        return
    req = app_root() / "requirements_winrt.txt"
    logger.warning("Missing WinRT packages %s — running pip install", missing)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req), "--break-system-packages"],
        check=False,
    )
    still = verify_winrt_dependencies()
    if still:
        logger.error("Missing WinRT speech dependencies: %s", winrt_install_hint(still))


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


def _preload_ml_stack() -> None:
    """Ensure sentence-transformers can import after torch."""
    try:
        if torch is None:
            import torch as _torch  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
        logger.info("ML stack preloaded")
    except Exception as exc:
        logger.warning("ML preload failed (paraphrase search may not work): %s", exc)


class DesktopApi:
    """Bridge the UI can call from JavaScript.

    The projector used to be a `window.open()` child window; inside WebView2
    that request escapes to the shell, which on a machine without a default
    browser association hands it to the Microsoft Store. Creating a real
    second webview window keeps it inside the app.
    """

    def __init__(self, url: str):
        self._url = url
        self._window = None

    def open_projector(self) -> bool:
        import webview

        if self._window is not None and self._window in webview.windows:
            self._window.show()
            return True
        self._window = webview.create_window(
            "WindowVerse — Projector",
            url=self._url,
            width=1280,
            height=720,
            background_color="#000000",
        )
        return True


def main():
    bootstrap_install()
    _ensure_winrt_dependencies()
    _preload_ml_stack()
    t = threading.Thread(target=_run_server, daemon=True, name="windowverse-server")
    t.start()
    if not _wait_for_port(port=PORT):
        print("Backend failed to start on port", PORT, file=sys.stderr)
        sys.exit(1)
    # HTTP static server starts inside server.run(); give it a moment
    time.sleep(0.5)

    import webview

    url = f"http://127.0.0.1:{HTTP_PORT}/ui/index.html"
    icon = resource_root() / "assets" / "windowverse.ico"
    if not icon.exists():
        icon = app_root() / "assets" / "windowverse.ico"

    api = DesktopApi(f"http://127.0.0.1:{HTTP_PORT}/ui/projector.html")
    window = webview.create_window(
        "WindowVerse — Live Service",
        url=url,
        width=1440,
        height=900,
        min_size=(1100, 700),
        background_color="#000000",
        js_api=api,
    )
    webview.start(debug=True)


if __name__ == "__main__":
    main()
