"""
app_config.py

Single source of truth for every tunable value in MultiVerse. Nothing in
the detection, display, or NDI pipeline should hardcode a threshold,
timeout, color, or size directly -- it should be read from here, and here
alone reads config/config.ini.

Why this file exists (root cause it fixes): config.ini has historically
documented values (vector_threshold, regex_threshold, cooldown_seconds,
book_memory_seconds...) that no code actually read -- the real numbers
were hardcoded inline in three different modules, silently drifting from
what the file claimed. That class of bug can't recur if there is exactly
ONE place that parses config.ini and everything else receives values via
constructor injection instead of reading the file (or re-declaring a
default) itself. Change a number in config.ini -> every consumer picks it
up next restart, with no code edit and no risk of missing a spot.

Each dataclass below is independently constructible (with explicit
defaults used only if a key is missing from config.ini -- never silently
different from what the file documents). A module that only needs
NDIConfig never has to know DetectionConfig exists -- that's the
"changing one thing independently" property being asked for.
"""

from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("multiverse.config")

DEFAULT_CONFIG_PATH = "config/config.ini"


# ── Section dataclasses ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class DetectionConfig:
    vector_threshold: float = 0.70
    regex_threshold: float = 0.75          # 0-1 scale; fuzzy book-name match floor
    min_overlap_ratio: float = 0.25        # hard gate: overlap-words / query-words
    cooldown_regex_seconds: float = 1.5
    cooldown_semantic_seconds: float = 4.0
    cooldown_narrative_seconds: float = 5.0
    dedup_seconds: float = 6.0             # suppress an identical verse re-firing within this window
    book_memory_seconds: float = 10.0      # how long a "pending book" guess stays valid
    min_semantic_words: int = 8


@dataclass(frozen=True)
class AppConfig:
    idle_timeout_seconds: float = 600.0
    transcript_tail_words: int = 8


@dataclass(frozen=True)
class NDIConfig:
    enabled: bool = True
    sender_name: str = "MultiVerse"
    width: int = 1920
    height: int = 1080
    fps: float = 3.0
    font_path: str = ""                    # "" = use a bundled/system default
    font_size: int = 64
    reference_font_size: int = 40
    text_color: tuple[int, int, int] = (255, 255, 255)
    background_color: tuple[int, int, int] = (0, 0, 0)
    background_alpha: int = 255            # 0 = fully transparent key, 255 = opaque
    margin: int = 80


@dataclass(frozen=True)
class LibraryConfig:
    data_root: str = "data"
    show_secondary_translation_by_default: bool = False
    # How often (seconds) the server re-scans data_root for new/removed
    # version or language folders while running, in addition to on every
    # new UI client connection. 0 disables the periodic scan (connect-time
    # scan still happens).
    rescan_interval_seconds: float = 30.0


@dataclass(frozen=True)
class MultiVerseConfig:
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    app: AppConfig = field(default_factory=AppConfig)
    ndi: NDIConfig = field(default_factory=NDIConfig)
    library: LibraryConfig = field(default_factory=LibraryConfig)
    db_path: str = "data/NKJV.SQLite3"
    translation: str = "NKJV"


# ── Parsing helpers ──────────────────────────────────────────────────────────

def _color_tuple(cfg: configparser.ConfigParser, section: str, key: str,
                  default: tuple[int, int, int]) -> tuple[int, int, int]:
    raw = cfg.get(section, key, fallback=None)
    if not raw:
        return default
    try:
        parts = [int(p.strip()) for p in raw.split(",")]
        if len(parts) != 3:
            raise ValueError
        return (parts[0], parts[1], parts[2])
    except ValueError:
        logger.warning("Malformed color '%s' in [%s] %s -- using default %s",
                        raw, section, key, default)
        return default


def load_config(path: str = DEFAULT_CONFIG_PATH) -> MultiVerseConfig:
    """
    Reads config/config.ini exactly once and returns a fully-typed,
    validated MultiVerseConfig. Missing keys fall back to the dataclass
    defaults above (which match what config.ini documents) -- a missing
    file or key never crashes startup, but it's always logged so a typo
    is visible instead of silently ignored.
    """
    cfg = configparser.ConfigParser()
    read_files = cfg.read(path)
    if not read_files:
        logger.warning("Could not read %s -- running entirely on built-in defaults", path)

    det_defaults = DetectionConfig()
    detection = DetectionConfig(
        vector_threshold=cfg.getfloat("detection", "vector_threshold",
                                       fallback=det_defaults.vector_threshold),
        regex_threshold=cfg.getfloat("detection", "regex_threshold",
                                      fallback=det_defaults.regex_threshold),
        min_overlap_ratio=cfg.getfloat("detection", "min_overlap_ratio",
                                        fallback=det_defaults.min_overlap_ratio),
        cooldown_regex_seconds=cfg.getfloat("detection", "cooldown_regex_seconds",
                                             fallback=det_defaults.cooldown_regex_seconds),
        cooldown_semantic_seconds=cfg.getfloat("detection", "cooldown_semantic_seconds",
                                                fallback=det_defaults.cooldown_semantic_seconds),
        cooldown_narrative_seconds=cfg.getfloat("detection", "cooldown_narrative_seconds",
                                                 fallback=det_defaults.cooldown_narrative_seconds),
        dedup_seconds=cfg.getfloat("detection", "dedup_seconds",
                                    fallback=det_defaults.dedup_seconds),
        book_memory_seconds=cfg.getfloat("detection", "book_memory_seconds",
                                          fallback=det_defaults.book_memory_seconds),
        min_semantic_words=cfg.getint("detection", "min_semantic_words",
                                       fallback=det_defaults.min_semantic_words),
    )

    app_defaults = AppConfig()
    app = AppConfig(
        idle_timeout_seconds=cfg.getfloat("app", "idle_timeout_seconds",
                                           fallback=app_defaults.idle_timeout_seconds),
        transcript_tail_words=cfg.getint("output", "transcript_tail_words",
                                          fallback=app_defaults.transcript_tail_words),
    )

    ndi_defaults = NDIConfig()
    ndi = NDIConfig(
        enabled=cfg.getboolean("ndi", "enabled", fallback=ndi_defaults.enabled),
        sender_name=cfg.get("ndi", "sender_name", fallback=ndi_defaults.sender_name),
        width=cfg.getint("ndi", "width", fallback=ndi_defaults.width),
        height=cfg.getint("ndi", "height", fallback=ndi_defaults.height),
        fps=cfg.getfloat("ndi", "fps", fallback=ndi_defaults.fps),
        font_path=cfg.get("ndi", "font_path", fallback=ndi_defaults.font_path),
        font_size=cfg.getint("ndi", "font_size", fallback=ndi_defaults.font_size),
        reference_font_size=cfg.getint("ndi", "reference_font_size",
                                        fallback=ndi_defaults.reference_font_size),
        text_color=_color_tuple(cfg, "ndi", "text_color", ndi_defaults.text_color),
        background_color=_color_tuple(cfg, "ndi", "background_color", ndi_defaults.background_color),
        background_alpha=cfg.getint("ndi", "background_alpha", fallback=ndi_defaults.background_alpha),
        margin=cfg.getint("ndi", "margin", fallback=ndi_defaults.margin),
    )

    lib_defaults = LibraryConfig()
    library = LibraryConfig(
        data_root=cfg.get("library", "data_root", fallback=lib_defaults.data_root),
        show_secondary_translation_by_default=cfg.getboolean(
            "library", "show_secondary_translation_by_default",
            fallback=lib_defaults.show_secondary_translation_by_default),
        rescan_interval_seconds=cfg.getfloat(
            "library", "rescan_interval_seconds",
            fallback=lib_defaults.rescan_interval_seconds),
    )

    return MultiVerseConfig(
        detection=detection,
        app=app,
        ndi=ndi,
        library=library,
        db_path=cfg.get("database", "db_path", fallback="data/NKJV.SQLite3"),
        translation=cfg.get("database", "translation", fallback="NKJV"),
    )
