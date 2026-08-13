"""Evaluate narrative anchor false-positive rate at configured thresholds."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from app_config import load_config
from bible_db import BibleDB
from bible_library import BibleLibrary
from detection_orchestrator import DetectionOrchestrator
from index_cache import load_or_build_index
from narrative_tracker import NarrativeTracker
from paths import ensure_user_dirs
from vocab_correction import purge_bad_corrections

from narrative_settings import DetectionUserSettings

purge_bad_corrections()
CFG = load_config()
DET = DetectionUserSettings()
NARRATIVE_CFG = DET.narrative_thresholds()

SHOULD_ANCHOR = [
    (
        "prodigal_son",
        "There was a man who had two sons and the younger one asked for his share "
        "of the inheritance and left home to live wildly until he had nothing left "
        "and ended up feeding pigs in a distant country",
    ),
    (
        "good_samaritan",
        "Jesus told a parable about a man going down from Jerusalem to Jericho who "
        "fell among thieves and was left half dead a priest and a Levite passed "
        "by but a Samaritan had compassion bound up his wounds",
    ),
    (
        "david_goliath",
        "The Philistines sent out their champion Goliath a giant who mocked Israel "
        "for forty days until young David the shepherd volunteered to fight him "
        "with a sling and five stones in the name of the Lord",
    ),
    (
        "creation",
        "In the beginning God created the heavens and the earth and the earth was "
        "without form and darkness was on the face of the deep and the Spirit of "
        "God moved upon the waters and God said let there be light",
    ),
    (
        "woman_issue_of_blood",
        "But there's this woman who had the issue called the issue of blood and "
        "she said to herself if I can just touch the hem of his garment",
    ),
]

SHOULD_NOT_ANCHOR = [
    "thank you for joining us this morning please be seated welcome everyone good to see you all here today in the house of the Lord",
    "the covenant of grace and redemption in systematic theology is a deep topic we will explore together in this series over the next few weeks",
    "let us stand and worship together now praise the Lord hallelujah amen we bless your holy name this morning church",
    "I think we should move on to the next point in our sermon outline and discuss what it means for our daily walk with Christ",
    "can you hear me at the back of the room is the microphone working properly today brothers and sisters",
    "For God so loved the world that is John three sixteen one of the most famous verses in all of scripture amen",
    "shepherd leadership principles for modern pastors in the church today require humility patience and a heart for the flock",
    "verse detection and paraphrase matching algorithms in software need careful tuning to avoid false positives during live services",
    "good morning church how is everyone doing today welcome we are glad you are here with us",
    "we will take up the offering after this song brothers and sisters please prepare your hearts",
    "my name is John and I am happy to be here with you tonight thank you for having me",
    "chapter three was a great discussion last week in small group we learned a lot together",
    "too many false positives in the detection system need fixing before the next service",
    "the weather has been really nice lately hasnt it wonderful sunshine for the picnic",
    "amen thank you Jesus hallelujah we bless your name and worship you with all our hearts today",
]


def make_tracker() -> NarrativeTracker:
    data_root = ensure_user_dirs()["data"]
    lib = BibleLibrary(str(data_root))
    lib.rescan()
    db = BibleDB(str(lib.resolve_primary_db("NKJV", "English")[2]))
    orch = DetectionOrchestrator(db, translation="NKJV")
    load_or_build_index(
        orch.vector_engine,
        db_path=db.db_path,
        cache_dir=str(data_root / "index_cache"),
        translation="NKJV",
    )
    return NarrativeTracker(
        orch.vector_engine._model,
        db,
        **NARRATIVE_CFG,
    )


def score_passage(nt: NarrativeTracker, text: str) -> tuple[str, float, float]:
    vec = nt._model.encode(
        [text], normalize_embeddings=True, show_progress_bar=False,
    ).astype("float32")[0]
    scores = nt._passage_embeddings @ vec
    idx = int(np.argmax(scores))
    sorted_scores = np.sort(scores)
    best = float(scores[idx])
    margin = best - float(sorted_scores[-2])
    return nt.passages[idx].title, best, margin


def would_anchor(nt: NarrativeTracker, text: str) -> bool:
    if len(text.split()) < nt._min_window_words:
        return False
    title, best, margin = score_passage(nt, text)
    return best >= nt._anchor_threshold and margin >= nt._anchor_margin


def main() -> int:
    nt = make_tracker()
    ui = DET.to_ui_dict()
    print(
        f"narrative_sensitivity={ui['narrative_sensitivity']} ({ui['narrative_label']}) "
        f"anchor={ui['anchor_threshold']} margin={ui['anchor_margin']} "
        f"min_words={ui['min_window_words']}"
    )

    missed = 0
    print("\n=== Should ANCHOR (story narration) ===")
    for label, text in SHOULD_ANCHOR:
        title, best, margin = score_passage(nt, text)
        ok = would_anchor(nt, text)
        print(
            f"{'OK' if ok else 'MISS'} [{best:.3f} m={margin:.3f}] "
            f"{label} -> {title}"
        )
        if not ok:
            missed += 1

    false_pos = 0
    print("\n=== Should NOT anchor (casual speech) ===")
    for text in SHOULD_NOT_ANCHOR:
        title, best, margin = score_passage(nt, text)
        hit = would_anchor(nt, text)
        if hit:
            false_pos += 1
            print(f"FALSE+ [{best:.3f} m={margin:.3f}] -> {title} | {text[:55]!r}")
        else:
            print(f"OK     [{best:.3f} m={margin:.3f}] | {text[:55]!r}")

    print(f"\nSummary: missed={missed}/{len(SHOULD_ANCHOR)} false_positives={false_pos}/{len(SHOULD_NOT_ANCHOR)}")
    return 1 if missed or false_pos else 0


if __name__ == "__main__":
    raise SystemExit(main())
