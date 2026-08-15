"""User-facing narrative detection sensitivity presets and persistence."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger("windowverse.narrative_settings")

USER_DETECTION_FILE = "detection_user.json"

# 1 = strictest … 5 = most forgiving. Default 3 (balanced).
NARRATIVE_SENSITIVITY_PRESETS: dict[int, dict[str, float | int | str]] = {
    1: {
        "label": "Strict",
        "hint": "Fewest false triggers — needs clear story wording.",
        "anchor_threshold": 0.55,
        "anchor_margin": 0.08,
        "dropout_threshold": 0.42,
        "advance_threshold": 0.50,
        "search_threshold": 0.55,
        "min_window_words": 22,
    },
    2: {
        "label": "Moderate",
        "hint": "Conservative — good for mixed sermon and announcements.",
        "anchor_threshold": 0.52,
        "anchor_margin": 0.06,
        "dropout_threshold": 0.41,
        "advance_threshold": 0.49,
        "search_threshold": 0.52,
        "min_window_words": 18,
    },
    3: {
        "label": "Balanced",
        "hint": "Recommended default — real stories without casual chatter.",
        "anchor_threshold": 0.47,
        "anchor_margin": 0.05,
        "dropout_threshold": 0.40,
        "advance_threshold": 0.48,
        "search_threshold": 0.47,
        "min_window_words": 15,
    },
    4: {
        "label": "Sensitive",
        "hint": "Catches shorter retellings — may occasionally misfire.",
        "anchor_threshold": 0.44,
        "anchor_margin": 0.04,
        "dropout_threshold": 0.38,
        "advance_threshold": 0.46,
        "search_threshold": 0.44,
        "min_window_words": 12,
    },
    5: {
        "label": "Very sensitive",
        "hint": "Most forgiving — use only if stories are still missed.",
        "anchor_threshold": 0.40,
        "anchor_margin": 0.03,
        "dropout_threshold": 0.36,
        "advance_threshold": 0.44,
        "search_threshold": 0.40,
        "min_window_words": 10,
    },
}


SILENCE_SAVE_PRESETS = (10, 20, 30, 60, 120)


@dataclass
class DetectionUserSettings:
    narrative_sensitivity: int = 3
    search_testament: str = "all"  # all | ot | nt
    silence_save_seconds: float = 10.0
    # Spoken navigation ("next verse") listens to the same dictation stream as
    # detection and is on by default; the master switch lives in Settings.
    voice_nav_enabled: bool = True
    voice_nav_auto_broadcast: bool = True
    voice_nav_wrap_books: bool = False
    voice_nav_respects_story_mode: bool = True
    # Operator-tuned spoken vocabulary: stock phrases switched off by label,
    # and extra phrases per intent (next/prev/repeat/clear/broadcast).
    voice_nav_disabled_keywords: list[str] = field(default_factory=list)
    voice_nav_custom_keywords: dict[str, list[str]] = field(default_factory=dict)
    # Speech detections keep going straight on air (pre-0.0.2.0 behaviour);
    # turn this off to make every verse — spoken or manual — go to preview
    # first and wait for Broadcast.
    transcript_auto_broadcast: bool = True
    # Marks a settings file written after voice navigation became opt-out;
    # older files are switched on once so the default actually reaches
    # operators who already have settings on disk.
    voice_nav_default_applied: bool = True

    def clamped_sensitivity(self) -> int:
        return max(1, min(5, int(self.narrative_sensitivity)))

    def narrative_thresholds(self) -> dict[str, float | int]:
        preset = NARRATIVE_SENSITIVITY_PRESETS[self.clamped_sensitivity()]
        return {
            "anchor_threshold": preset["anchor_threshold"],
            "anchor_margin": preset["anchor_margin"],
            "dropout_threshold": preset["dropout_threshold"],
            "advance_threshold": preset["advance_threshold"],
            "search_threshold": preset["search_threshold"],
            "min_window_words": preset["min_window_words"],
        }

    def clamped_search_testament(self) -> str:
        st = (self.search_testament or "all").strip().lower()
        return st if st in ("all", "ot", "nt") else "all"

    def clamped_silence_save_seconds(self) -> float:
        return max(5.0, min(600.0, float(self.silence_save_seconds or 10.0)))

    def to_ui_dict(self) -> dict:
        level = self.clamped_sensitivity()
        preset = NARRATIVE_SENSITIVITY_PRESETS[level]
        silence = self.clamped_silence_save_seconds()
        preset_match = next((p for p in SILENCE_SAVE_PRESETS if abs(p - silence) < 0.5), None)
        return {
            "narrative_sensitivity": level,
            "narrative_label": preset["label"],
            "narrative_hint": preset["hint"],
            "search_testament": self.clamped_search_testament(),
            "silence_save_seconds": silence,
            "silence_save_preset": preset_match if preset_match is not None else "custom",
            "voice_nav_enabled": bool(self.voice_nav_enabled),
            "voice_nav_auto_broadcast": bool(self.voice_nav_auto_broadcast),
            "voice_nav_wrap_books": bool(self.voice_nav_wrap_books),
            "voice_nav_respects_story_mode": bool(self.voice_nav_respects_story_mode),
            "voice_nav_disabled_keywords": list(self.voice_nav_disabled_keywords or []),
            "voice_nav_custom_keywords": {
                k: list(v or []) for k, v in (self.voice_nav_custom_keywords or {}).items()
            },
            "transcript_auto_broadcast": bool(self.transcript_auto_broadcast),
            **self.narrative_thresholds(),
        }


def load_detection_user(path: Path) -> DetectionUserSettings:
    if not path.exists():
        return DetectionUserSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        known = set(DetectionUserSettings.__dataclass_fields__)
        filtered = {k: v for k, v in data.items() if k in known}
        if not filtered.get("voice_nav_default_applied"):
            filtered["voice_nav_enabled"] = True
            filtered["voice_nav_default_applied"] = True
        return DetectionUserSettings(**filtered)
    except Exception:
        logger.exception("Failed to load %s — using defaults", path)
        return DetectionUserSettings()


def save_detection_user(path: Path, settings: DetectionUserSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
