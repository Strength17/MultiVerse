"""Resolve install paths for dev repo vs PyInstaller frozen bundle."""
from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger("windowverse.paths")

_LEGACY_USER_ROOT = Path.home() / "Documents" / "MultiVerse"
_USER_ROOT = Path.home() / "Documents" / "WindowVerse"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_root()


def _migrate_legacy_user_data() -> None:
    """One-time copy from Documents/MultiVerse to Documents/WindowVerse."""
    if not _LEGACY_USER_ROOT.exists():
        return
    if _USER_ROOT.exists() and any(_USER_ROOT.iterdir()):
        return
    try:
        shutil.copytree(_LEGACY_USER_ROOT, _USER_ROOT, dirs_exist_ok=True)
        logger.info("Migrated user data from %s to %s", _LEGACY_USER_ROOT, _USER_ROOT)
    except Exception:
        logger.exception("Could not migrate legacy user data — using WindowVerse path only")


def user_data_root() -> Path:
    _migrate_legacy_user_data()
    if not _USER_ROOT.exists() and _LEGACY_USER_ROOT.exists():
        try:
            _USER_ROOT.mkdir(parents=True, exist_ok=True)
            for item in _LEGACY_USER_ROOT.iterdir():
                dest = _USER_ROOT / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                elif not dest.exists():
                    shutil.copy2(item, dest)
            logger.info("Seeded WindowVerse user folder from legacy MultiVerse data")
        except Exception:
            logger.exception("Partial legacy migration — continuing with WindowVerse path")
    _USER_ROOT.mkdir(parents=True, exist_ok=True)
    return _USER_ROOT


def _env(name: str, legacy: str | None = None) -> str | None:
    val = os.environ.get(name)
    if val:
        return val
    if legacy:
        return os.environ.get(legacy)
    return None


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
    env = _env("WINDOWVERSE_CONFIG", "MULTIVERSE_CONFIG")
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

    cfg = str(user_cfg if user_cfg.exists() else bundled_cfg)
    data = str(dirs["data"])
    logs = str(dirs["logs"])
    os.environ.setdefault("WINDOWVERSE_CONFIG", cfg)
    os.environ.setdefault("WINDOWVERSE_DATA_ROOT", data)
    os.environ.setdefault("WINDOWVERSE_LOGS_DIR", logs)
    os.environ.setdefault("MULTIVERSE_CONFIG", cfg)
    os.environ.setdefault("MULTIVERSE_DATA_ROOT", data)
    os.environ.setdefault("MULTIVERSE_LOGS_DIR", logs)

    _migrate_bible_data(bundled / "data", dirs["data"])

    return {
        "config": Path(os.environ["WINDOWVERSE_CONFIG"]),
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
    en_target = nkjv_en / "NKJV.sqlite3"
    for src in (
        bundled_data / "NKJV.SQLite3",
        bundled_data / "NKJV.sqlite3",
        bundled_data / "NKJV" / "English" / "NKJV.sqlite3",
    ):
        if src.exists() and not en_target.exists():
            try:
                shutil.copy2(src, en_target)
                logger.info("Seeded English NKJV database to %s", en_target)
            except Exception:
                pass
            break

    for name in ("bible_vectors.index", "bible_verse_map.pkl"):
        src = bundled_data / name
        dst = user_data / name
        if src.exists() and not dst.exists():
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
