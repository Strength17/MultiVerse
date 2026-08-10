"""
vector_search.py

Semantic (paraphrase) verse detection: embeds the transcript chunk and
the full verse corpus with sentence-transformers, searches via FAISS,
then re-ranks the top-k FAISS candidates using word overlap + distinctive
biblical-term weighting + word order — not just raw cosine similarity.

Model choice (researched): all-MiniLM-L6-v2 — 22M params, ~14k
sentences/sec on a standard CPU, 384-dim. This is the right choice for a
real-time, low-RAM, CPU-fallback-friendly pipeline; the larger
all-mpnet-base-v2 has somewhat better retrieval quality but is ~5x slower
and not worth it for short verse-length text where MiniLM already
performs well.

This same `search_paraphrase()` function is meant to back BOTH the live
auto-detection pipeline and a future manual "Context mode" search UI —
one engine, two entry points, per the architecture spec.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

logger = logging.getLogger("multiverse.vector_search")

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Distinctive theological vocabulary gets extra weight in re-ranking —
# generic words ("the", "and", "God") appear in thousands of verses and
# shouldn't dominate the match; rare/specific terms are stronger signals.
BIBLICAL_TERM_WEIGHT = {
    "condemnation": 2.0, "righteousness": 2.0, "covenant": 2.0,
    "propitiation": 2.5, "redemption": 2.0, "sanctification": 2.0,
    "justification": 2.0, "atonement": 2.5, "reconciliation": 2.0,
    "transgression": 2.0, "iniquity": 2.0, "abomination": 2.0,
    "tabernacle": 2.0, "covenant": 2.0, "begotten": 2.0,
    "shepherd": 1.5, "vineyard": 1.5, "wilderness": 1.5,
    "prophecy": 1.5, "discipline": 1.5, "stewardship": 1.5,
}

_WORD_RE = re.compile(r"[a-z']+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


@dataclass
class VerseCandidate:
    book: str
    book_number: int
    chapter: int
    verse: int
    text: str
    translation: str
    faiss_score: float  # cosine similarity from FAISS, 0-1ish


class VectorSearchEngine:
    """
    Holds the loaded embedding model + FAISS index for the full verse
    corpus, and exposes search_paraphrase() for both the live pipeline
    and manual "Context mode" search.
    """

    def __init__(self, bible_db, translation: str = "NKJV"):
        self.bible_db = bible_db
        self.translation = translation
        self._model = None
        self._index = None
        self._verse_lookup: list[VerseCandidate] = []
        self._lock = threading.Lock()
        self._embedding_cache: dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------
    def _load_model(self):
        if self._model is not None:
            return

        import os
        from sentence_transformers import SentenceTransformer

        # Offline-first by default: this tool needs to run at live events
        # where venue WiFi is unreliable or absent, so it must NEVER
        # silently depend on internet access. local_files_only=True is the
        # documented, reliable mechanism for this (the HF_HUB_OFFLINE env
        # var alone has known buggy interactions in some library versions
        # where it skips the local cache check instead of using it -- so
        # we set both, with local_files_only as the primary guarantee).
        allow_download = os.environ.get("MULTIVERSE_ALLOW_MODEL_DOWNLOAD", "0") == "1"

        if not allow_download:
            os.environ["HF_HUB_OFFLINE"] = "1"

        try:
            logger.info("Loading embedding model %s (offline=%s)",
                        EMBEDDING_MODEL_NAME, not allow_download)
            self._model = SentenceTransformer(
                EMBEDDING_MODEL_NAME,
                local_files_only=not allow_download,
            )
        except Exception as e:
            if allow_download:
                raise  # genuine failure even with network allowed -- surface it
            raise RuntimeError(
                f"Embedding model '{EMBEDDING_MODEL_NAME}' is not in the local "
                f"cache and offline mode is on, so it can't be downloaded now.\n\n"
                f"Fix: run this ONCE on a machine with internet access "
                f"(or temporarily enable it on this one):\n\n"
                f"  set MULTIVERSE_ALLOW_MODEL_DOWNLOAD=1\n"
                f"  python -c \"from sentence_transformers import SentenceTransformer; "
                f"SentenceTransformer('{EMBEDDING_MODEL_NAME}')\"\n\n"
                f"After that one-time download (~90MB, cached to "
                f"~/.cache/huggingface), this app runs fully offline forever."
            ) from e
        finally:
            if not allow_download:
                os.environ.pop("HF_HUB_OFFLINE", None)  # don't leak this into unrelated code

    def build_index(self):
        """
        Embeds every verse in the Bible DB once and builds a FAISS index.
        Call this once at startup (or load a cached index from disk if
        present — see index_cache.py).
        """
        self._load_model()
        import faiss

        rows = self.bible_db.fetch_all_verses(self.translation)
        logger.info("Embedding %d verses for semantic search index...", len(rows))

        texts = [r["text"] for r in rows]
        embeddings = self._model.encode(
            texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True
        ).astype("float32")

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors == cosine similarity
        index.add(embeddings)

        self._index = index
        self._verse_lookup = [
            VerseCandidate(
                book=r["book"], book_number=r["book_number"],
                chapter=r["chapter"], verse=r["verse"],
                text=r["text"], translation=self.translation,
                faiss_score=0.0,
            )
            for r in rows
        ]
        logger.info("FAISS index built: %d verses, dim=%d", len(rows), dim)

    # ------------------------------------------------------------------
    @lru_cache(maxsize=256)
    def _cached_embed(self, text: str) -> bytes:
        """
        Cache embeddings for repeated/similar transcript chunks (Pewbeam-
        documented behavior: "common queries are cached for near-instant
        results on repeat"). Returns raw bytes since lru_cache needs a
        hashable return isn't required, but caching the ndarray directly
        is fine too — bytes avoids any aliasing surprises on reuse.
        """
        self._load_model()
        vec = self._model.encode([text], normalize_embeddings=True, show_progress_bar=False).astype("float32")
        return vec.tobytes()

    def _embed_query(self, text: str) -> np.ndarray:
        raw = self._cached_embed(text)
        return np.frombuffer(raw, dtype="float32").reshape(1, -1)

    # ------------------------------------------------------------------
    def search_paraphrase(self, query: str, top_k: int = 8) -> dict | None:
        """
        Main entry point — used by both the live detection pipeline and
        manual Context-mode search. Embeds the query, retrieves top_k
        FAISS candidates, re-ranks them, and returns the best match
        above the detection floor (0.35), or None.
        """
        if self._index is None:
            raise RuntimeError("Vector index not built — call build_index() first")

        query = query.strip()
        if not query:
            return None

        with self._lock:
            qvec = self._embed_query(query)
            scores, idxs = self._index.search(qvec, top_k)

        candidates = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= len(self._verse_lookup):
                continue
            cand = self._verse_lookup[idx]
            # External pre-built indexes (loaded via index_cache.load_external_index)
            # can populate _verse_lookup with plain dicts instead of VerseCandidate
            # dataclass instances. cand.book crashes on a dict -- this was the
            # AttributeError seen on every chunk in production. Handle both shapes.
            if isinstance(cand, dict):
                get = cand.get
            else:
                get = lambda key, default=None, _c=cand: getattr(_c, key, default)
            candidates.append({
                "book": get("book"), "book_number": get("book_number"),
                "chapter": get("chapter"), "verse": get("verse"),
                "text": get("text"), "translation": get("translation", self.translation),
                "score": float(score),
            })

        if not candidates:
            return None

        best = self._rerank(query, candidates)
        if best is None:
            return None

        # Detection floor: config.ini has always documented this as 0.70
        # (`[detection] vector_threshold`), but no code ever actually read
        # that value -- the real floor here was a hardcoded 0.35, which is
        # why filler/meta speech ("I think you are printing...") was
        # auto-triggering real verses at 0.60-0.84 confidence. Honor the
        # documented 0.70 floor for real.
        confidence = self._score_to_confidence(best["combined_score"])
        if confidence < 0.70:
            return None

        return {
            "source": "semantic",
            "book": best["book"],
            "book_number": best["book_number"],
            "chapter": best["chapter"],
            "verse": best["verse"],
            "text": best["text"],
            "translation": best["translation"],
            "confidence": confidence,
            "raw_faiss_score": best["score"],
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _rerank(query: str, candidates: list[dict]) -> dict | None:
        """
        Re-rank FAISS top-k candidates using word overlap and biblical
        term weighting, not just raw cosine similarity — a meaningful
        accuracy improvement over naive top-1 FAISS selection.
        """
        query_words = set(_tokenize(query))

        best = None
        best_score = -1.0
        for cand in candidates:
            cand_text = cand.get("text") or ""
            if not cand_text:
                # Malformed/incomplete row in the pre-built index (e.g.
                # missing "text" key) -- skip rather than crash on
                # _tokenize(None).lower().
                cand["combined_score"] = -1.0
                continue
            cand_words = set(_tokenize(cand_text))
            overlap = len(query_words & cand_words)
            term_bonus = sum(
                BIBLICAL_TERM_WEIGHT.get(w, 0) for w in (query_words & cand_words)
            )
            # Light word-order signal: reward candidates whose words appear
            # in the same relative order as the query (cheap LCS-ish proxy
            # via bigram overlap rather than full edit distance, to keep
            # this well under budget on weak CPUs).
            order_bonus = VectorSearchEngine._bigram_overlap(query, cand_text)

            combined = (
                cand["score"]
                + (overlap * 0.02)
                + (term_bonus * 0.01)
                + (order_bonus * 0.015)
            )
            cand["combined_score"] = combined
            if combined > best_score:
                best_score = combined
                best = cand

        return best if best_score > -1.0 else None

    @staticmethod
    def _bigram_overlap(a: str, b: str) -> float:
        a_words = _tokenize(a)
        b_words = _tokenize(b)
        a_bigrams = set(zip(a_words, a_words[1:]))
        b_bigrams = set(zip(b_words, b_words[1:]))
        if not a_bigrams or not b_bigrams:
            return 0.0
        return len(a_bigrams & b_bigrams) / max(len(a_bigrams), 1)

    @staticmethod
    def _score_to_confidence(combined_score: float) -> float:
        """
        Maps the combined re-rank score onto the documented semantic
        confidence band (0.35-0.89), since raw cosine + bonus terms
        don't naturally land in a 0-1 range that matches that band.
        """
        # Cosine similarity (from normalized embeddings) is already 0-1;
        # bonuses add a modest boost on top. Clamp into the 0.35-0.89
        # display band so this lines up with config.ini's documented
        # semantic_confidence_min/max.
        scaled = min(max(combined_score, 0.0), 1.0)
        return round(0.35 + scaled * 0.54, 3)  # maps [0,1] -> [0.35, 0.89]