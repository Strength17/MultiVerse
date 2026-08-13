"""Full pipeline test: vocab correction + orchestrator + server cooldown path."""
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

PHRASES = [
    "John chapter 3 verse 16",
    "John chapter one verse one",
    "John chapter 1 verse 1",
    "book of John chapter 3 verse 16",
    "Romans chapter 8 verse 1",
    "John 3 16",
    "John 3:16",
    "turn to John chapter 3 verse 16",
    "in John chapter 3 verse 16",
    "the book of John chapter 3 verse 16",
    "John chapter three verse sixteen",
    "let's look at John chapter 3 verse 16",
    "as it says in John chapter 3 verse 16",
    "Romance chapter one verse one",
    "ecclesiastics chapter 2 the 16",
    "ecclesiastics chapter 2 verse 16",
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


def detect_split(raw_parts: list[str]) -> dict:
    orch = make_orch()
    r = {"triggered": False}
    base = time.time()
    for i, p in enumerate(raw_parts):
        corrected = correct_text(p)
        r = orch.detect(
            corrected,
            chunk_start=base + i,
            chunk_end=base + i + 1,
        )
    return r


def main():
    failed = 0
    print("=== Single-chunk (with vocab correction) ===")
    for raw in PHRASES:
        orch = make_orch()
        corrected = correct_text(raw)
        r = detect_phrase(orch, raw)
        ok = r.get("triggered") and r.get("source") == "regex"
        status = "OK" if ok else "FAIL"
        print(f"{status} raw={raw!r}")
        if corrected != raw:
            print(f"      corrected={corrected!r}")
        if ok:
            print(f"      -> {r['book']} {r['chapter']}:{r['verse']}")
        else:
            print(f"      -> {r}")
            failed += 1

    print("\n=== Split chunks ===")
    splits = [
        (["John", "chapter 3 verse 16"], "John", 3, 16),
        (["turn to John", "chapter 3 verse 16"], "John", 3, 16),
        (["book of John", "chapter 3 verse 16"], "John", 3, 16),
        (["John chapter 3", "verse 16"], "John", 3, 16),
        (["John chapter one", "verse one"], "John", 1, 1),
    ]
    for parts, book, ch, v in splits:
        r = detect_split(parts)
        ok = (
            r.get("triggered")
            and r.get("source") == "regex"
            and r.get("book") == book
            and r.get("chapter") == ch
            and r.get("verse") == v
        )
        print(f"{'OK' if ok else 'FAIL'} {' / '.join(parts)!r} -> {r.get('book')} {r.get('chapter')}:{r.get('verse')} src={r.get('source')}")
        if not ok:
            failed += 1

    print("\n=== Stale wrong context (Jeremiah pollution) ===")
    orch = make_orch()
    # Simulate prior wrong semantic context update
    orch.context.update(240, "Jeremiah", 5)
    orch.context.last_update -= 25
    r = detect_phrase(orch, "John chapter one verse one")
    ok = r.get("triggered") and r.get("book") == "John"
    print(f"{'OK' if ok else 'FAIL'} after stale Jeremiah ctx -> {r.get('book')} {r.get('chapter')}:{r.get('verse')}")
    if not ok:
        failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
