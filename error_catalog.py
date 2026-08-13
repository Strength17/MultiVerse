"""Structured system-log codes and one-line fix hints for the UI."""
from __future__ import annotations

CATALOG: dict[str, dict[str, str]] = {
    "mic_start_failed": {
        "level": "error",
        "fix": "If the message mentions winrt or globalization, run: pip install -r requirements_winrt.txt --break-system-packages — then restart. Otherwise: Sidebar → Microphone → pick the correct device; Windows Settings → Privacy → Microphone → allow access.",
    },
    "not_ready": {
        "level": "warn",
        "fix": "Wait until loading reaches 100%, then press Start again.",
    },
    "semantic_index_empty": {
        "level": "warn",
        "fix": "Copy bible_vectors.index and bible_verse_map.pkl into Documents\\WindowVerse\\data\\.",
    },
    "matched_reference_missing_from_db": {
        "level": "error",
        "fix": "Check your Bible DB under data\\NKJV\\English\\ — run inspect_bible_db.py on the file.",
    },
    "reference_out_of_range": {
        "level": "warn",
        "fix": "The reference heard is outside this book's chapter/verse range — verify what was spoken.",
    },
    "startup_self_check_failed": {
        "level": "error",
        "fix": "Run inspect_bible_db.py on your DB; confirm book-number mapping matches the schema.",
    },
    "ndi_unavailable": {
        "level": "warn",
        "fix": "Install the free NDI Runtime from ndi.video, then restart Window Verse.",
    },
    "winrt_deps_missing": {
        "level": "error",
        "fix": "Run: pip install -r requirements_winrt.txt --break-system-packages — then restart Window Verse.",
    },
    "db_schema_error": {
        "level": "error",
        "fix": "Run inspect_bible_db.py data\\NKJV\\French\\FreBBB.db --sample",
    },
    "transcript_saved": {
        "level": "info",
        "fix": "",
    },
    "disconnected": {
        "level": "error",
        "fix": "Backend stopped or lost connection — restart Window Verse.",
    },
    "generic": {
        "level": "warn",
        "fix": "See Documents\\WindowVerse\\logs\\windowverse.log for details.",
    },
}


def log_entry(code: str, message: str, fix: str | None = None) -> dict:
    meta = CATALOG.get(code, CATALOG["generic"])
    return {
        "type": "system_log",
        "level": meta["level"],
        "code": code,
        "message": message,
        "fix": fix if fix is not None else meta.get("fix", ""),
    }
