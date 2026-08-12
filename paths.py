"""Resolve install paths for dev repo vs PyInstaller frozen bundle."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_root()


def user_data_root() -> Path:
    root = Path.home() / "Documents" / "MultiVerse"
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_user_dirs() -> dict[str, Path]:
    base = user_data_root()
    dirs = {
        "data": base / "data",
        "logs": base / "logs",
        "transcription": base / "Transcription",
        "backgrounds": base / "data" / "backgrounds",
        "config": base / "config",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)

    old_transcripts = base / "Transcripts"
    if old_transcripts.exists() and old_transcripts.is_dir():
        dest = dirs["transcription"]
        for f in old_transcripts.iterdir():
            if f.is_file():
                target = dest / f.name
                if not target.exists():
                    shutil.move(str(f), str(target))
        try:
            if not any(old_transcripts.iterdir()):
                old_transcripts.rmdir()
        except OSError:
            pass

    return dirs


def config_path() -> Path:
    env = os.environ.get("MULTIVERSE_CONFIG")
    if env:
        return Path(env)
    user_cfg = user_data_root() / "config" / "config.ini"
    if user_cfg.exists():
        return user_cfg
    bundled = app_root() / "config" / "config.ini"
    return bundled


def bootstrap_install() -> dict[str, Path]:
    """First-run setup: user folders, default config copy, README seeds."""
    dirs = ensure_user_dirs()
    bundled = app_root()

    user_cfg = dirs["config"] / "config.ini"
    bundled_cfg = bundled / "config" / "config.ini"
    if not user_cfg.exists() and bundled_cfg.exists():
        shutil.copy2(bundled_cfg, user_cfg)

    readme = bundled / "data" / "README_DATA.txt"
    if readme.exists() and not (dirs["data"] / "README_DATA.txt").exists():
        shutil.copy2(readme, dirs["data"] / "README_DATA.txt")

    bg_readme = bundled / "data" / "backgrounds" / "README.txt"
    if bg_readme.exists() and not (dirs["backgrounds"] / "README.txt").exists():
        shutil.copy2(bg_readme, dirs["backgrounds"] / "README.txt")

    os.environ.setdefault("MULTIVERSE_CONFIG", str(user_cfg if user_cfg.exists() else bundled_cfg))
    os.environ.setdefault("MULTIVERSE_DATA_ROOT", str(dirs["data"]))
    os.environ.setdefault("MULTIVERSE_LOGS_DIR", str(dirs["logs"]))

    _migrate_bible_data(bundled / "data", dirs["data"])

    return {
        "config": Path(os.environ["MULTIVERSE_CONFIG"]),
        "data_root": dirs["data"],
        "logs": dirs["logs"],
        "transcription": dirs["transcription"],
        "backgrounds": dirs["backgrounds"],
        "config_dir": dirs["config"],
    }


def _migrate_bible_data(bundled_data: Path, user_data: Path) -> None:
    """Move flat FreBBB.db into NKJV/French/ and ensure folder layout."""
    flat_fre = bundled_data / "FreBBB.db"
    user_fre = user_data / "FreBBB.db"
    target_dir = user_data / "NKJV" / "French"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "FreBBB.db"

    for src in (flat_fre, user_fre):
        if src.exists() and not target.exists():
            try:
                shutil.copy2(src, target)
            except Exception:
                pass

    nkjv_en = user_data / "NKJV" / "English"
    nkjv_en.mkdir(parents=True, exist_ok=True)
