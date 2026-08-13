"""Integration tests: explicit references, including STT split chunks."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from paths import ensure_user_dirs


def _orch():
    data_root = ensure_user_dirs()["data"]
    lib = BibleLibrary(str(data_root))
    lib.rescan()
    db = BibleDB(str(lib.resolve_primary_db("NKJV", "English")[2]))
    o = DetectionOrchestrator(db)
    o._index_built = True
    return o


def _detect_chunks(parts: list[str]) -> dict:
    o = _orch()
    r = {"triggered": False}
    for i, p in enumerate(parts):
        r = o.detect(p, chunk_start=float(i), chunk_end=float(i + 1))
    return r


def test_single_explicit():
    o = _orch()
    r = o.detect("John chapter 3 verse 16")
    assert r.get("triggered") and r.get("book") == "John" and r.get("verse") == 16


def test_split_turn_to_john():
    r = _detect_chunks(["turn to John", "chapter 3 verse 16"])
    assert r.get("triggered"), r
    assert r["book"] == "John" and r["chapter"] == 3 and r["verse"] == 16


def test_split_book_name_only():
    r = _detect_chunks(["John", "chapter 3 verse 16"])
    assert r.get("triggered"), r
    assert r["book"] == "John" and r["chapter"] == 3 and r["verse"] == 16


def test_split_book_of_john():
    r = _detect_chunks(["book of John", "chapter 3 verse 16"])
    assert r.get("triggered"), r
    assert r["book"] == "John" and r["chapter"] == 3 and r["verse"] == 16


def test_split_chapter_then_verse():
    r = _detect_chunks(["John chapter 3", "verse 16"])
    assert r.get("triggered"), r
    assert r["book"] == "John" and r["chapter"] == 3 and r["verse"] == 16


def main():
    tests = [
        test_single_explicit,
        test_split_turn_to_john,
        test_split_book_name_only,
        test_split_book_of_john,
        test_split_chapter_then_verse,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print("OK", t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", t.__name__, e)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
