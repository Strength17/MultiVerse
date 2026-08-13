"""Regression: Matthew 5:8 paraphrase must not drift to Jeremiah/Proverbs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from index_cache import load_or_build_index
from paths import ensure_user_dirs

data_root = ensure_user_dirs()["data"]
lib = BibleLibrary(str(data_root))
lib.rescan()
resolved = lib.resolve_primary_db("NKJV", "English")
db_path = str(resolved[2])
db = BibleDB(db_path)
orch = DetectionOrchestrator(db, translation="NKJV")
load_or_build_index(
    orch.vector_engine,
    db_path=db_path,
    cache_dir=str(data_root / "index_cache"),
    translation="NKJV",
)
orch._index_built = True

CASES = [
    ("clean beatitude", "Blessed are the pure in heart for they shall see God", "Matthew", 5, 8),
    (
        "beatitude + polluted tail (was Jeremiah 5:24)",
        "Blessed are the pure in heart for they shall see God and the Lord gives rain in its season",
        "Matthew", 5, 8,
    ),
]

failed = 0
for label, text, exp_book, exp_ch, exp_v in CASES:
    r = orch.detect(text)
    ok = (
        r.get("triggered")
        and r.get("book") == exp_book
        and r.get("chapter") == exp_ch
        and r.get("verse") == exp_v
    )
    status = "OK" if ok else "FAIL"
    print(f"{status} [{label}] -> {r.get('book')} {r.get('chapter')}:{r.get('verse')} ({r.get('confidence')})")
    if not ok:
        failed += 1
    orch.buffer.clear()
    orch._two_chunk_deque.clear()

# Two-chunk split (distinct timestamps)
orch2 = DetectionOrchestrator(db, translation="NKJV")
load_or_build_index(
    orch2.vector_engine, db_path=db_path,
    cache_dir=str(data_root / "index_cache"), translation="NKJV",
)
orch2._index_built = True
r1 = orch2.detect("Blessed are the pure in heart", chunk_start=1.0, chunk_end=2.0)
r2 = orch2.detect("for they shall see God", chunk_start=2.0, chunk_end=3.0)
r = r2 if r2.get("triggered") else r1
ok = r.get("book") == "Matthew" and r.get("chapter") == 5 and r.get("verse") == 8
print(f"{'OK' if ok else 'FAIL'} [two-chunk split] -> {r.get('book')} {r.get('chapter')}:{r.get('verse')}")
if not ok:
    failed += 1

sys.exit(1 if failed else 0)
