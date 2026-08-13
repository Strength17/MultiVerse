"""Check detection for issue-of-blood narration sample."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from index_cache import load_or_build_index
from narrative_tracker import NarrativeTracker
from paths import ensure_user_dirs
from vocab_correction import correct_text

TEXT = (
    "But there's this woman who had the issue called the issue of blood and "
    "she said to herself if I can just touch the hem of his coming"
)


def main():
    data_root = ensure_user_dirs()["data"]
    lib = BibleLibrary(str(data_root))
    lib.rescan()
    db = BibleDB(str(lib.resolve_primary_db("NKJV", "English")[2]))
    orch = DetectionOrchestrator(db, translation="NKJV", vector_threshold=0.80)
    load_or_build_index(
        orch.vector_engine,
        db_path=db.db_path,
        cache_dir=str(data_root / "index_cache"),
        translation="NKJV",
    )
    orch._index_built = True
    r = orch.detect(correct_text(TEXT))
    print("semantic:", r.get("triggered"), r.get("book"), r.get("chapter"), r.get("verse"), r.get("confidence"))

    nt = NarrativeTracker(orch.vector_engine._model, db)
    vec = nt._model.encode([TEXT], normalize_embeddings=True, show_progress_bar=False).astype("float32")[0]
    scores = nt._passage_embeddings @ vec
    idx = int(np.argmax(scores))
    ss = np.sort(scores)
    print("narrative best:", nt.passages[idx].title, float(scores[idx]), float(scores[idx] - ss[-2]))


if __name__ == "__main__":
    main()
