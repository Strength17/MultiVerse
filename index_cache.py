"""
index_cache.py

Embedding the full Bible (~31,000 verses) with all-MiniLM-L6-v2 takes a
few seconds even on a fast machine and meaningfully longer on the weakest
CPU-only hardware this project targets. Re-doing that on every app launch
is wasted time the moment the verse text or translation hasn't changed.

This module persists the built FAISS index + verse lookup table to disk
and validates the cache against a hash of the source DB file, so edits to
the Bible DB (e.g. swapping translations) correctly invalidate the cache
rather than silently serving stale embeddings.
"""

from __future__ import annotations

import hashlib
import logging
import pickle
from pathlib import Path

logger = logging.getLogger("multiverse.index_cache")


def _file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()[:16]


def load_external_index(vector_engine, faiss_index_path: str | Path,
                         verse_lookup_path: str | Path,
                         lookup_format: str = "pickle") -> None:
    """
    Load a FAISS index + verse lookup table you already built yourself —
    used when you have a pre-existing index (e.g. all 31,102 NKJV verses
    already embedded) and want the orchestrator to use it directly,
    with zero re-embedding and zero hash/cache-validation logic getting
    in the way.

    faiss_index_path: path to a .faiss / .index file readable by
        faiss.read_index() (anything written with faiss.write_index()
        qualifies — IndexFlatIP, IndexFlatL2, IVF, HNSW, etc).

    verse_lookup_path: path to the parallel verse metadata, i.e. the
        list that maps FAISS row i -> verse info. Must be ordered
        identically to how the index was built (row 0 of the index
        corresponds to lookup[0], etc).

    lookup_format: "pickle" for a pickled list[dict] (or list of
        VerseCandidate-shaped dicts) — the most common case if you
        built the index in Python — or "json" for a JSON array of
        objects with at least book/book_number/chapter/verse/text keys.

    This function does NOT validate, hash, or compare against any other
    index. It trusts the files you point it at completely and loads them
    as-is — by design, since the whole point is to skip any rebuild path.
    """
    import faiss
    import json

    faiss_index_path = Path(faiss_index_path)
    verse_lookup_path = Path(verse_lookup_path)

    if not faiss_index_path.exists():
        raise FileNotFoundError(f"FAISS index not found at {faiss_index_path}")
    if not verse_lookup_path.exists():
        raise FileNotFoundError(f"Verse lookup table not found at {verse_lookup_path}")

    logger.info("Loading EXTERNAL pre-built index from %s (no rebuild, no re-embedding)",
                faiss_index_path)

    vector_engine._load_model()  # still needed to embed live QUERIES, not the corpus
    vector_engine._index = faiss.read_index(str(faiss_index_path))

    if lookup_format == "pickle":
        with open(verse_lookup_path, "rb") as f:
            raw_lookup = pickle.load(f)
    elif lookup_format == "json":
        with open(verse_lookup_path, "r", encoding="utf-8") as f:
            raw_lookup = json.load(f)
    else:
        raise ValueError(f"Unknown lookup_format: {lookup_format!r}")

    # Normalize to the VerseCandidate-shaped dicts vector_search.py expects,
    # tolerating either dict rows or VerseCandidate-like objects.
    # Pre-built pickles can use slightly different key names than what
    # vector_search.py expects (e.g. "verse_text"/"content" instead of
    # "text"). Map known aliases and drop rows with no usable text.
    _ALIASES = {
        "text": ("text", "verse_text", "content", "verse"),
        "book": ("book", "book_name", "book_title"),
        "book_number": ("book_number", "book_id", "book_num", "bookid"),
        "verse": ("verse", "verse_num", "verse_number", "v"),
        "chapter": ("chapter", "chapter_num", "chapter_number"),
    }

    def _get_alias(d: dict, canonical: str, lower_key_map: dict):
        # Case-insensitive: compare against the row's ACTUAL keys lower-cased,
        # not just the exact-cased alias strings.
        for key in _ALIASES.get(canonical, (canonical,)):
            actual_key = lower_key_map.get(key.lower())
            if actual_key is not None and d[actual_key]:
                return d[actual_key]
        return d.get(canonical)

    normalized = []
    skipped = 0
    recovered_from_db = 0
    _logged_sample_keys = False
    for row in raw_lookup:
        if isinstance(row, dict):
            if not _logged_sample_keys:
                logger.info("First external-lookup row has keys: %s", list(row.keys()))
                _logged_sample_keys = True
            lower_key_map = {k.lower(): k for k in row.keys()}
            text_val = _get_alias(row, "text", lower_key_map)
            book_val = _get_alias(row, "book", lower_key_map)
            # Resolve canonical verse/chapter/book_number up front, from
            # whatever alias key this pickle actually used (e.g. verse_num,
            # book_id) -- regardless of whether text needs DB recovery
            # below. Previously only "text"/"book" were ever normalized
            # onto the dict; "verse" stayed whatever raw key the row
            # happened to have (verse_num, never "verse" itself), so
            # vector_search.py's get("verse") always returned None even
            # on a correct, high-confidence match.
            book_num_val = _get_alias(row, "book_number", lower_key_map)
            chapter_val = _get_alias(row, "chapter", lower_key_map)
            verse_val = _get_alias(row, "verse", lower_key_map)
            book_number_val = int(book_num_val) if book_num_val is not None else None
            chapter_val = int(chapter_val) if chapter_val is not None else None
            verse_val = int(verse_val) if verse_val is not None else None

            if not text_val:
                # No text-shaped field at all (not even a casing mismatch --
                # this pickle just never stored verse text, only identifiers
                # like book_id/verse_num). That's a valid design: the FAISS
                # vectors were built FROM the text, but the text itself lives
                # in the Bible DB, not duplicated into the pickle. Recover it
                # by looking the identifiers up against bible_db instead of
                # discarding the row.
                if book_number_val is not None and chapter_val is not None and verse_val is not None:
                    raw_book_num = book_number_val
                    # This pickle's book id (e.g. key "book_id") is the DB's
                    # OWN raw numbering, not canonical -- see bible_db's
                    # startup warning ("DB book-number scheme differs from
                    # bible_books.py's hardcoded numbering"). Reverse-map to
                    # canonical FIRST. Trying it as canonical first (the old
                    # order) could silently "succeed" by coincidence --
                    # lookup_verse's numeric fallback returns the raw value
                    # unchanged when it isn't a recognized canonical number,
                    # which happened to match this DB's own column by luck
                    # and produced results tagged "book": "730" (a raw DB
                    # id) instead of a canonical name.
                    canon = vector_engine.bible_db._book_number_map_reverse.get(raw_book_num)
                    db_row = vector_engine.bible_db.lookup_verse(
                        canon if canon is not None else raw_book_num,
                        chapter_val, verse_val,
                        translation=vector_engine.translation,
                    )
                    if db_row is None and canon is not None:
                        # Fall back to treating the id as already-canonical,
                        # in case this particular pickle wasn't built from
                        # the DB's raw numbering after all.
                        db_row = vector_engine.bible_db.lookup_verse(
                            raw_book_num, chapter_val, verse_val,
                            translation=vector_engine.translation,
                        )
                    if db_row is not None:
                        text_val = db_row["text"]
                        # Always take the canonical name/number bible_db
                        # resolved, even if the row already carried a "book"
                        # field -- semantic results now go through the same
                        # canonical-name resolution regular lookups use.
                        book_val = db_row.get("book") or book_val
                        book_number_val = db_row.get("book_number", book_number_val)
                        recovered_from_db += 1

            if not text_val:
                skipped += 1
                continue
            normalized.append({
                **row, "text": text_val, "book": book_val,
                "book_number": book_number_val, "chapter": chapter_val, "verse": verse_val,
            })
        else:
            normalized.append({
                "book": row.book, "book_number": row.book_number,
                "chapter": row.chapter, "verse": row.verse,
                "text": row.text, "translation": getattr(row, "translation", "NKJV"),
                "faiss_score": 0.0,
            })

    vector_engine._verse_lookup = normalized

    if vector_engine._index.ntotal != len(normalized):
        logger.warning(
            "Index size (%d) and lookup table size (%d) don't match — "
            "row order may be misaligned. Verify these files came from "
            "the same build.", vector_engine._index.ntotal, len(normalized)
        )

    logger.info("External index loaded: %d verses, ready for queries — no embedding work done",
                len(normalized))
    if recovered_from_db:
        logger.info("Recovered text for %d rows via Bible DB lookup (pickle stored "
                    "identifiers only, no text field)", recovered_from_db)
    if skipped and normalized:
        logger.warning("Skipped %d rows from external lookup with no usable text field", skipped)
    elif skipped and not normalized:
        # Every row was skipped -- semantic search is completely dead, not
        # just degraded. This is a hard failure, not a warning: the app
        # will run and look fine (regex still works) while silently never
        # matching a single paraphrase for the rest of the session.
        logger.error(
            "ALL %d rows from external lookup had no usable text field — "
            "semantic/paraphrase detection is COMPLETELY DISABLED this "
            "session. The pickle's dict keys don't match any known alias "
            "(expected one of: text/verse_text/content/verse). Rebuild "
            "bible_verse_map.pkl or fix its key names.", skipped,
        )


def cache_paths_for_db(cache_dir: str | Path, db_path: str | Path,
                       translation: str = "NKJV") -> tuple[Path, Path]:
    """Return (faiss_path, lookup_path) for a given Bible DB file hash."""
    cache_dir = Path(cache_dir)
    db_hash = _file_hash(db_path)
    return (
        cache_dir / f"verse_index_{translation}_{db_hash}.faiss",
        cache_dir / f"verse_lookup_{translation}_{db_hash}.pkl",
    )


def load_or_build_index(vector_engine, db_path: str | Path, cache_dir: str | Path,
                         translation: str = "NKJV",
                         progress_callback=None) -> None:
    """
    Populates vector_engine._index and vector_engine._verse_lookup either
    from a valid on-disk cache, or by building fresh and writing the
    cache for next time. Mutates vector_engine in place (mirrors the
    shape build_index() would have produced).
    """
    import faiss

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    index_path, lookup_path = cache_paths_for_db(cache_dir, db_path, translation)

    if index_path.exists() and lookup_path.exists():
        logger.info("Loading cached semantic index from %s", index_path)
        vector_engine._load_model()  # still need the model loaded for queries
        vector_engine._index = faiss.read_index(str(index_path))
        with open(lookup_path, "rb") as f:
            vector_engine._verse_lookup = pickle.load(f)
        logger.info("Cached index loaded: %d verses", len(vector_engine._verse_lookup))
        return

    logger.info(
        "No valid cache found (hash=%s) — building fresh index",
        _file_hash(db_path),
    )
    vector_engine.build_index(progress_callback=progress_callback)

    faiss.write_index(vector_engine._index, str(index_path))
    with open(lookup_path, "wb") as f:
        pickle.dump(vector_engine._verse_lookup, f)
    logger.info("Index cached to %s for fast startup next time", index_path)

    # Clean up stale cache files from previous translations/DB versions so
    # the cache directory doesn't grow unbounded across DB updates.
    for stale in cache_dir.glob(f"verse_index_{translation}_*.faiss"):
        if stale != index_path:
            stale.unlink(missing_ok=True)
    for stale in cache_dir.glob(f"verse_lookup_{translation}_*.pkl"):
        if stale != lookup_path:
            stale.unlink(missing_ok=True)
