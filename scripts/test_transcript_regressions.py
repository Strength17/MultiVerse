"""Regression tests from WindowVerse_2026-08-12 session transcript failures."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from paths import ensure_user_dirs
from vocab_correction import correct_text, purge_bad_corrections

purge_bad_corrections()

CASES = [
    ("Romance chapter one verse one", "Romans", 1, 1),
    ("romance chapter one verse one", "Romans", 1, 1),
    ("ecclesiastics chapter 2 the 16", "Ecclesiastes", 2, 16),
    ("ecclesiastics chapter 2 verse 16", "Ecclesiastes", 2, 16),
]


def make_orch():
    data_root = ensure_user_dirs()["data"]
    lib = BibleLibrary(str(data_root))
    lib.rescan()
    db = BibleDB(str(lib.resolve_primary_db("NKJV", "English")[2]))
    o = DetectionOrchestrator(db)
    o._index_built = True
    return o


def detect_phrase(orch, raw: str) -> dict:
    corrected = correct_text(raw)
    return orch.detect(corrected, chunk_start=time.time(), chunk_end=time.time() + 1)


def main() -> int:
    orch = make_orch()
    failed = 0
    for raw, book, chapter, verse in CASES:
        result = detect_phrase(orch, raw)
        ok = (
            result.get("triggered")
            and result.get("book") == book
            and result.get("chapter") == chapter
            and result.get("verse") == verse
        )
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {raw!r}")
        if not ok:
            failed += 1
            print(f"       corrected={correct_text(raw)!r}")
            print(f"       got={result}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
