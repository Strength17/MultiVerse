"""Regression tests for verse reference detection."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reference_context import ReferenceContext
from verse_detector import detect_direct_reference


class _FakeDB:
    def validate_reference(self, book_number, chapter, verse):
        if book_number == 430 and chapter == 1 and verse == 1:
            return {"valid": True}
        if book_number == 430 and chapter == 11 and verse == 1:
            return {"valid": True}
        if book_number == 430 and chapter == 2 and verse == 2:
            return {"valid": True}
        if book_number == 430 and chapter == 1 and verse <= 51:
            return {"valid": True}
        if book_number == 430 and chapter == 2 and verse <= 25:
            return {"valid": True}
        if book_number == 430 and chapter == 11:
            return {"valid": True, "reason": "chapter_only"}
        return {"valid": False, "reason": "out_of_range"}


def _detect(text: str, ctx: ReferenceContext | None = None):
    ctx = ctx or ReferenceContext(timeout_seconds=20)
    return detect_direct_reference(text, ctx, bible_db=_FakeDB())


def test_john_chapter_1_verse_1():
    r = _detect("John chapter 1 verse 1")
    assert r and r["book"] == "John" and r["chapter"] == 1 and r["verse"] == 1


def test_john_1_1_no_keywords():
    r = _detect("John 1 1")
    assert r and r["chapter"] == 1 and r["verse"] == 1


def test_split_chapter_then_verse():
    ctx = ReferenceContext(timeout_seconds=20)
    _detect("John chapter 1", ctx)
    r = _detect("verse 1", ctx)
    assert r and r["chapter"] == 1 and r["verse"] == 1


def test_collapsed_john_11_with_verse_keyword():
    r = _detect("John 11 verse 1")
    assert r and r["chapter"] == 1 and r["verse"] == 1, r


def test_stale_context_bare_verse_blocked():
    ctx = ReferenceContext(timeout_seconds=20, bare_verse_max_age=8)
    ctx.update(430, "John", 2)
    ctx.last_update -= 15
    r = _detect("verse 1", ctx)
    assert r is None or r.get("handled") or (r.get("chapter") == 1 and r.get("verse") == 1)


def main():
    tests = [
        test_john_chapter_1_verse_1,
        test_john_1_1_no_keywords,
        test_split_chapter_then_verse,
        test_collapsed_john_11_with_verse_keyword,
        test_stale_context_bare_verse_blocked,
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
