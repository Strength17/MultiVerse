"""
vocab_correction.py

Windows' free-dictation engine has no public API for injecting a custom
vocabulary into open dictation -- SpeechRecognitionListConstraint only
supports closed command lists, not continuous speech. So instead of trying
to prevent mishears of names like "Nebuchadnezzar" or "Deuteronomy", this
catches and fixes them AFTER recognition, before detection runs:

  1. Fuzzy-match every 1-3 word window of the transcript against the 66
     canonical book names in bible_books.py, using rapidfuzz.
  2. Any correction made gets written to data/corrections_learned.json, so
     the next time that exact mishear happens it's a direct dict lookup --
     no re-solving, and it only gets better the more you use the app.

Runs BEFORE detection_orchestrator.detect(), so verse_detector's regex
matching always sees the corrected text.

Caveat (real, not hidden): fuzzy matching single common words against 66
names can rarely false-positive. Threshold is set high (85/100) to keep
this rare; if you ever see an unrelated word get "corrected" into a book
name, delete its entry from data/corrections_learned.json.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from rapidfuzz import fuzz, process

from bible_books import (
    BOOKS,
    STT_BOOK_ALIASES,
    apply_stt_book_aliases,
    is_reference_signal,
    resolve_stt_book_alias,
)

logger = logging.getLogger("windowverse.vocab_correction")

_LEARNED_PATH = Path(__file__).parent / "data" / "corrections_learned.json"
_CANONICAL_NAMES = [name for _, name, _ in BOOKS]
_FUZZY_THRESHOLD = 85  # rapidfuzz score 0-100 -- below this, leave the word alone
_WINDOW_SIZES = (3, 2, 1)  # try longest phrase match first ("Song of Solomon")

# Never rewrite windows that already carry an explicit reference skeleton —
# "John chapter one verse one" must reach verse_detector intact.
_REF_STRUCTURE = re.compile(
    r"\b(chapter|chapters|ch\.|verse|verses|ver\.)\b|\d",
    re.IGNORECASE,
)

# WRatio (used below) boosts substring/partial matches -- great for real
# mishears ("book of Romans" -> "Romans", the filler comes BEFORE the real
# name), terrible for short phrases that happen to share filler words with
# a longer name ("of romance" scores 85.5 against "Song of Solomon" purely
# off shared "of" + partial character overlap -- pure coincidence, not a
# mishear). The reliable signal: every real "filler + name" mishear has the
# spoken phrase AT LEAST AS LONG AS the canonical name it's being corrected
# to (filler only adds length, it never shrinks below the target). A phrase
# shorter than the name it would become is a red flag, not a mishear.
_MIN_LENGTH_RATIO = 1.0  # len(phrase) must be >= 100% of len(canonical name)


def _length_ratio_ok(phrase: str, canonical: str) -> bool:
    if not canonical:
        return False
    return (len(phrase) / len(canonical)) >= _MIN_LENGTH_RATIO

# Common single-word function words that must never become a book name, no
# matter what score rapidfuzz gives them ("I" -> "Isaiah", "the" -> "Esther").
# A single generic word scoring high against a 5-8 letter proper noun is
# always a false positive, not a real mishear -- checked BEFORE the learned
# dict lookup, since a bad entry can already be saved there from before this
# guard existed (see purge_bad_corrections below).
_NEVER_CORRECT = frozenset({
    "i", "a", "an", "the", "is", "in", "on", "to", "of", "and", "or", "but",
    "he", "she", "it", "we", "you", "they", "them", "his", "her", "its",
    "so", "as", "at", "by", "for", "if", "me", "my", "no", "not", "now",
    "up", "us", "am", "be", "do", "go", "how", "who", "why", "yes", "was",
    "are", "were", "had", "has", "have", "this", "that", "these", "those",
})


def _has_reference_structure(phrase: str) -> bool:
    return bool(_REF_STRUCTURE.search(phrase))


def _load_learned() -> dict[str, str]:
    if _LEARNED_PATH.exists():
        try:
            return json.loads(_LEARNED_PATH.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Could not read %s -- starting fresh", _LEARNED_PATH)
    return {}


def _save_learned(mapping: dict[str, str]) -> None:
    try:
        _LEARNED_PATH.parent.mkdir(parents=True, exist_ok=True)
        _LEARNED_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logger.exception("Could not write %s", _LEARNED_PATH)


_learned = _load_learned()


def purge_bad_corrections() -> int:
    """Remove entries from the learned-corrections dict that violate the
    guards added after they were saved (single stopwords, digit-containing
    keys). Safe to call any time; intended to run once at server startup so
    a machine with an already-corrupted corrections_learned.json self-heals
    without a manual step. Returns the number of entries removed."""
    global _learned
    bad_keys = [
        key for key in _learned
        if (key in _NEVER_CORRECT and " " not in key)
        or any(ch.isdigit() for ch in key)
        or _has_reference_structure(key)
        or not _length_ratio_ok(key, _learned[key])
    ]
    for key in bad_keys:
        del _learned[key]
    if bad_keys:
        _save_learned(_learned)
        logger.info("Purged %d bad learned correction(s): %r", len(bad_keys), bad_keys)
    return len(bad_keys)


def _correct_contextual_book_tokens(words: list[str]) -> list[str]:
    """Fix isolated book mishears when the next word signals a reference."""
    out = list(words)
    for i in range(len(out)):
        nxt = out[i + 1] if i + 1 < len(out) else None
        if nxt is None or not is_reference_signal(nxt):
            continue
        key = out[i].lower().strip(".,;:!?\"'")
        if key in _NEVER_CORRECT:
            continue
        alias = resolve_stt_book_alias(out[i], nxt)
        if alias:
            out[i] = alias
            if key not in _learned:
                _learned[key] = alias
            continue
        if key in _learned:
            out[i] = _learned[key]
            continue
        if _has_reference_structure(key) or any(ch.isdigit() for ch in key):
            continue
        best = process.extractOne(
            out[i], _CANONICAL_NAMES, scorer=fuzz.WRatio, score_cutoff=_FUZZY_THRESHOLD
        )
        if best is not None:
            canonical, score, _ = best
            if _length_ratio_ok(out[i], canonical) and canonical.lower() != key:
                _learned[key] = canonical
                _save_learned(_learned)
                logger.info(
                    "Learned contextual correction: %r -> %r (score=%.0f)",
                    out[i], canonical, score,
                )
                out[i] = canonical
    return out


def correct_text(text: str) -> str:
    """Best-effort correction of misheard Bible proper nouns. Never raises --
    returns the original text unmodified on any internal failure."""
    if not text or not text.strip():
        return text

    try:
        words = _correct_contextual_book_tokens(text.split())
        out: list[str] = []
        i = 0
        n = len(words)
        while i < n:
            matched = False
            for size in _WINDOW_SIZES:
                if i + size > n:
                    continue
                phrase = " ".join(words[i:i + size])
                key = phrase.lower().strip(".,;:!?")

                # Explicit references must never be rewritten — corrupted
                # learned entries like "john chapter one" -> "John" were
                # stripping chapter/verse numbers before regex detection.
                if _has_reference_structure(key):
                    continue

                # Real book-name mishears never involve digits -- the ASR
                # already gets numbers right, so a phrase like "verse 1"
                # scoring high against "1 Chronicles" is a false positive,
                # not a real correction. Skip this window entirely.
                if any(ch.isdigit() for ch in key):
                    continue

                # Single common words (stopwords/pronouns) never get
                # corrected, even if already saved in the learned dict from
                # before this guard existed -- checked before the dict
                # lookup so a stale bad entry can't fire either.
                if size == 1 and key in _NEVER_CORRECT:
                    continue

                if key in _learned:
                    out.append(_learned[key])
                    i += size
                    matched = True
                    break

                best = process.extractOne(
                    phrase, _CANONICAL_NAMES, scorer=fuzz.WRatio, score_cutoff=_FUZZY_THRESHOLD
                )
                if best is not None:
                    canonical, score, _ = best
                    if not _length_ratio_ok(phrase, canonical):
                        continue
                    if _has_reference_structure(phrase):
                        continue
                    if canonical.lower() != phrase.lower():
                        _learned[key] = canonical
                        _save_learned(_learned)
                        logger.info("Learned correction: %r -> %r (score=%.0f)",
                                    phrase, canonical, score)
                    out.append(canonical)
                    i += size
                    matched = True
                    break
            if not matched:
                out.append(words[i])
                i += 1
        return apply_stt_book_aliases(" ".join(out))
    except Exception:
        logger.exception("vocab_correction failed -- passing text through unmodified")
        return text
