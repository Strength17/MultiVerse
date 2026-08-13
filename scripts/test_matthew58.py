"""Quick test: Matthew 5:8 paraphrase detection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from index_cache import load_or_build_index, load_external_index
from paths import ensure_user_dirs

data_root = ensure_user_dirs()["data"]
lib = BibleLibrary(str(data_root))
lib.rescan()
resolved = lib.resolve_primary_db("NKJV", "English")
db_path = str(resolved[2]) if resolved else str(data_root / "NKJV" / "English" / "NKJV.sqlite3")
print("DB:", db_path)
db = BibleDB(str(db_path))
orch = DetectionOrchestrator(db, translation="NKJV")

ext_faiss = data_root / "bible_vectors.index"
ext_pkl = data_root / "bible_verse_map.pkl"
cache_dir = data_root / "index_cache"

for label, loader in [
    ("CACHED", lambda: load_or_build_index(orch.vector_engine, db_path=db_path, cache_dir=str(cache_dir), translation="NKJV")),
    ("EXTERNAL", lambda: load_external_index(orch.vector_engine, ext_faiss, ext_pkl) if ext_faiss.exists() else None),
]:
    if label == "EXTERNAL" and not ext_faiss.exists():
        print("\n=== EXTERNAL index not found, skip ===")
        continue
    print(f"\n=== {label} index ===")
    loader()
    orch._index_built = True
    phrase = "Blessed are the pure in heart for they shall see God"
    r = orch.detect(phrase)
    print(
        "DETECT:",
        r.get("book"),
        r.get("chapter"),
        r.get("verse"),
        r.get("source"),
        r.get("confidence"),
    )
    ve = orch.vector_engine
    qvec = ve._embed_query(phrase)
    scores, idxs = ve._index.search(qvec, 5)
    for score, idx in zip(scores[0], idxs[0]):
        cand = ve._verse_lookup[idx]
        book = cand.get("book") if isinstance(cand, dict) else cand.book
        ch = cand.get("chapter") if isinstance(cand, dict) else cand.chapter
        v = cand.get("verse") if isinstance(cand, dict) else cand.verse
        text = cand.get("text") if isinstance(cand, dict) else cand.text
        print(f"  top: {book} {ch}:{v} score={score:.3f} | {str(text)[:70]}")
