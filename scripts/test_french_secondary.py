"""Verify French secondary text attaches to detections."""
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
    orch.vector_engine, db_path=db_path,
    cache_dir=str(data_root / "index_cache"), translation="NKJV",
)
orch._index_built = True

r = orch.detect("Blessed are the pure in heart for they shall see God")
assert r.get("book_number"), "detection must include book_number"
print("book_number", r["book_number"])

sec_db = lib.get_db("NKJV", "French")
fr = sec_db.lookup_verse(r["book_number"], r["chapter"], r["verse"])
print("French:", fr["text"][:80])
assert fr and "c" in fr["text"].lower() or "Dieu" in fr["text"]
print("OK")
