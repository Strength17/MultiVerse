"""Evaluate paraphrase false-positive rate at vector_threshold=0.80."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app_config import load_config
from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from index_cache import load_or_build_index
from paths import ensure_user_dirs
from vocab_correction import correct_text, purge_bad_corrections

purge_bad_corrections()
CFG = load_config()

SHOULD_TRIGGER = [
    ("Blessed are the pure in heart for they shall see God", "Matthew", 5, 8),
    ("For God so loved the world that he gave his only begotten Son", "John", 3, 16),
    ("In the beginning God created the heavens and the earth", "Genesis", 1, 1),
    ("There is therefore now no condemnation to those who are in Christ Jesus", "Romans", 8, 1),
    ("The Lord is my shepherd I shall not want", "Psalms", 23, 1),
    ("Love is patient love is kind", "1 Corinthians", 13, 4),
    ("Trust in the Lord with all your heart", "Proverbs", 3, 5),
    ("Be still and know that I am God", "Psalms", 46, 10),
]

SHOULD_NOT_TRIGGER = [
    "thank you for joining us this morning",
    "please be seated welcome everyone",
    "good morning church how are you doing",
    "I think we should move on to the next point",
    "the weather has been really nice lately",
    "let us stand and worship together now",
    "amen thank you Jesus hallelujah praise God",
    "too many false positives in the detection system",
    "can you hear me at the back of the room",
    "we will take up the offering after this song",
    "my name is John and I am happy to be here",
    "chapter three was a great discussion last week",
    "verse detection and paraphrase matching algorithms",
    "the covenant of grace and redemption in theology",
    "shepherd leadership principles for modern pastors",
]


def make_orch():
    data_root = ensure_user_dirs()["data"]
    lib = BibleLibrary(str(data_root))
    lib.rescan()
    db = BibleDB(str(lib.resolve_primary_db("NKJV", "English")[2]))
    o = DetectionOrchestrator(
        db,
        translation="NKJV",
        vector_threshold=CFG.detection.vector_threshold,
        min_overlap_ratio=CFG.detection.min_overlap_ratio,
        min_semantic_words=CFG.detection.min_semantic_words,
    )
    load_or_build_index(
        o.vector_engine,
        db_path=db.db_path,
        cache_dir=str(data_root / "index_cache"),
        translation="NKJV",
    )
    o._index_built = True
    return o


def detect(orch, text: str) -> dict:
    return orch.detect(correct_text(text))


def main():
    orch = make_orch()
    threshold = CFG.detection.vector_threshold
    print(f"vector_threshold={threshold}")

    missed = 0
    print("\n=== Should TRIGGER (paraphrase) ===")
    for text, book, ch, v in SHOULD_TRIGGER:
        r = detect(orch, text)
        ok = r.get("triggered") and r.get("book") == book and r.get("chapter") == ch and r.get("verse") == v
        src = r.get("source")
        conf = r.get("confidence")
        print(f"{'OK' if ok else 'MISS'} [{conf}] {book} {ch}:{v} | {text[:55]!r} -> {r.get('book')} {r.get('chapter')}:{r.get('verse')} ({src})")
        if not ok:
            missed += 1
        orch.buffer.clear()
        orch._two_chunk_deque.clear()

    false_pos = 0
    print("\n=== Should NOT trigger ===")
    for text in SHOULD_NOT_TRIGGER:
        r = detect(orch, text)
        hit = r.get("triggered")
        if hit:
            false_pos += 1
            print(f"FALSE+ [{r.get('confidence')}] {r.get('book')} {r.get('chapter')}:{r.get('verse')} | {text!r}")
        else:
            print(f"OK     — | {text!r}")
        orch.buffer.clear()
        orch._two_chunk_deque.clear()

    print(f"\nSummary: missed={missed}/{len(SHOULD_TRIGGER)} false_positives={false_pos}/{len(SHOULD_NOT_TRIGGER)}")
    return 1 if missed or false_pos else 0


if __name__ == "__main__":
    raise SystemExit(main())
