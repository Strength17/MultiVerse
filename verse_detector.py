"""
verse_detector.py  —  V4

Adds, on top of V3's pattern coverage:
  - Single-chapter-book exception (Obadiah, Philemon, 2/3 John, Jude):
    bare "Book N" is UNAMBIGUOUS (verse N, chapter 1) -- fires immediately.
  - Pending/confirm state machine for every OTHER book: bare "Book N" is
    ambiguous (chapter guess vs. this-chapter's-verse-N), so it now PRIMES
    a pending guess instead of assuming chapter -- see reference_context.py.
    A following "verse N" CONFIRMS it (medium confidence); an explicit full
    reference DISCARDS it; a ~60s timeout falls back to chapter-only.
  - Ordinal-word normalization: "one/two/three Corinthians" (WinRT-style
    cardinal STT output) now normalizes the same as "first/second/third".
  - "and" support: "chapter 8 and verse 1".
  - Verse ranges: "verses 28 through 30" / "28 to 30" / "28-30".
  - Book-only priming: "turn to Romans" / "turn in your bibles to Romans"
    primes book context with no chapter yet (explicit phrase-gated, so
    every passing mention of a book name doesn't reset context).

Detection layers (priority order):
  1. Standard notation: "John 3:16"
  2. Spoken form (+ optional "and"): "Romans chapter 8 verse 28" / "...and verse 28"
  3. Spoken form, no 'chapter' keyword: "Psalm 23 verse 1"
  3b. Verse range: "John chapter 3 verses 16 through 18"
  4. Chapter-only: "James chapter 4" (confirms context, no verse yet)
  4b. Book-only: "turn to Romans" (primes book, chapter unknown)
  5. Single-chapter-book bare number: "Jude 3" -> Jude 1:3, immediate
  6. Multi-chapter bare number: "John 11" -> PRIMES pending, no trigger yet
  7. Bare verse: "verse 10" -> confirms pending OR resolves confirmed context
  8. Spoken numbers: "john three sixteen"
  9. Fuzzy spoken fallback (rapidfuzz + word2number)

Speed: regex paths <5ms. Fuzzy path <15ms (only reached when strict patterns fail).
Confidence: 90-97% regex explicit, 90% bare-verse-vs-confirmed-context,
78% bare-number-confirmed-via-pending (medium band), 78% fuzzy.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from bible_books import (
    ALL_NAMES_SORTED,
    NAME_TO_BOOK,
    ORDINAL_BOOK_STEMS,
    SINGLE_CHAPTER_BOOKS,
    apply_stt_book_aliases,
)
from reference_context import ReferenceContext

logger = logging.getLogger("multiverse.verse_detector")

# ── Spoken number tables ──────────────────────────────────────────────────────
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]

_WORD_TO_NUM: dict[str, int] = {w: i for i, w in enumerate(_ONES)}
for _i, _w in enumerate(_TENS):
    if _w:
        _WORD_TO_NUM[_w] = _i * 10
_WORD_TO_NUM["hundred"] = 100


def _words_to_number(phrase: str) -> int | None:
    """'twenty eight' → 28, 'one hundred nineteen' → 119, 'three' → 3."""
    tokens = phrase.lower().replace("-", " ").split()
    total = 0
    found = False
    for tok in tokens:
        if tok == "hundred" and total:
            total *= 100
            found = True
        elif tok in _WORD_TO_NUM:
            total += _WORD_TO_NUM[tok]
            found = True
        else:
            return None
    return total if found else None


# ── Ordinal / cardinal book-prefix normalization ──────────────────────────────
# "first/second/third Corinthians" -> "1/2/3 corinthians" (existing).
# "one/two/three Corinthians"      -> "1/2/3 corinthians" (NEW -- WinRT and
# other STT engines sometimes emit the cardinal instead of the ordinal).
# Scoped to ORDINAL_BOOK_STEMS only, so a stray "one", "two", or "three"
# elsewhere in a sentence ("verse one hundred") is never touched.
_STEM_ALT = "|".join(re.escape(s) for s in ORDINAL_BOOK_STEMS)
_STEM_NO_JOHN = "|".join(re.escape(s) for s in ORDINAL_BOOK_STEMS if s != "john")
_ORDINAL_WORD_RE = re.compile(rf'\bfirst\s+(?={_STEM_ALT})', re.IGNORECASE)
_ORDINAL_WORD_RE2 = re.compile(rf'\bsecond\s+(?={_STEM_ALT})', re.IGNORECASE)
_ORDINAL_WORD_RE3 = re.compile(rf'\bthird\s+(?={_STEM_ALT})', re.IGNORECASE)
_CARDINAL_ONE_RE = re.compile(rf'\bone\s+(?={_STEM_NO_JOHN})', re.IGNORECASE)
_CARDINAL_TWO_RE = re.compile(rf'\btwo\s+(?={_STEM_ALT})', re.IGNORECASE)
_CARDINAL_THREE_RE = re.compile(rf'\bthree\s+(?={_STEM_ALT})', re.IGNORECASE)
# Numeral+suffix ordinal forms: "1st corinthians" -> "1 corinthians". WinRT
# (and other STT engines) sometimes render the spoken ordinal as a digit
# plus written-out suffix instead of either the word form ("first") or the
# bare cardinal ("one") already handled above. Previously NONE of the
# normalization rules covered this shape, so "1st Corinthians" matched no
# book pattern at all -- not even partially -- and every reference spoken
# that way (plus every bare "verse N" depending on it for context) silently
# failed. Scoped to ORDINAL_BOOK_STEMS same as the others.
_ORDINAL_SUFFIX_1_RE = re.compile(rf'\b1st\s+(?={_STEM_ALT})', re.IGNORECASE)
_ORDINAL_SUFFIX_2_RE = re.compile(rf'\b2nd\s+(?={_STEM_ALT})', re.IGNORECASE)
_ORDINAL_SUFFIX_3_RE = re.compile(rf'\b3rd\s+(?={_STEM_ALT})', re.IGNORECASE)


_NUM_TOKEN = r"\d{1,3}|[a-z]+(?:[\s\-][a-z]+){0,2}"
_CHAPTER_THE_VERSE = re.compile(
    rf"\bchapter\s+({_NUM_TOKEN})\s+the\s+({_NUM_TOKEN})\b",
    re.IGNORECASE,
)


def _normalize_stt_artifacts(text: str) -> str:
    """Fix common WinRT shape errors before regex matching."""
    text = _CHAPTER_THE_VERSE.sub(r"chapter \1 verse \2", text)
    return text


def _normalize_prefixes(text: str) -> str:
    """'first corinthians' -> '1 corinthians', 'two timothy' -> '2 timothy',
    '1st corinthians' -> '1 corinthians'. Cardinal forms ('one', 'two',
    'three') and numeral+suffix forms ('1st', '2nd', '3rd') are normalized
    the SAME as ordinal word forms, but only immediately before a known
    ordinal-book stem (samuel/kings/chronicles/corinthians/thessalonians/
    timothy/peter/john) -- see ORDINAL_BOOK_STEMS -- so unrelated numbers
    are never touched."""
    t = _ORDINAL_WORD_RE.sub('1 ', text)
    t = _ORDINAL_WORD_RE2.sub('2 ', t)
    t = _ORDINAL_WORD_RE3.sub('3 ', t)
    t = _CARDINAL_ONE_RE.sub('1 ', t)
    t = _CARDINAL_TWO_RE.sub('2 ', t)
    t = _CARDINAL_THREE_RE.sub('3 ', t)
    t = _ORDINAL_SUFFIX_1_RE.sub('1 ', t)
    t = _ORDINAL_SUFFIX_2_RE.sub('2 ', t)
    t = _ORDINAL_SUFFIX_3_RE.sub('3 ', t)
    return t


def _parse_number_token(token: str) -> int | None:
    token = token.strip().lower()
    if token in ("to", "too"):
        return 1
    if token.isdigit():
        return int(token)
    return _words_to_number(token)


# ── Regex patterns ────────────────────────────────────────────────────────────
def _book_pattern() -> str:
    escaped = [re.escape(name) for name in ALL_NAMES_SORTED]
    return "(?:" + "|".join(escaped) + ")"


_BOOK_RE  = _book_pattern()
_NUMWORD  = r"[a-z]+(?:[\s\-][a-z]+){0,2}"
_NUM_OR_WORD = rf"(?:\d{{1,3}}|{_NUMWORD})"
# "and" support: a bare comma OR the word "and" (or both) may separate
# "chapter N" from "verse N" -- matches natural speech ("chapter 8 and verse 1").
_JOINER = r"\s*(?:,\s*)?(?:and\s+)?"

_STANDARD_NOTATION = re.compile(
    # '/' accepted alongside ':' and '.' -- WinRT's on-device dictation
    # renders spoken "four twenty-four" as the date-style "4/24" rather
    # than "4:24", so the separator class must include it or the whole
    # reference silently falls through to the ambiguous bare-number path.
    rf"\b({_BOOK_RE})\.?\s+(\d{{1,3}})\s*[:./]\s*(\d{{1,3}})\b",
    re.IGNORECASE,
)
_SPOKEN_FORM = re.compile(
    rf"\b({_BOOK_RE})\s+chapter\s+({_NUM_OR_WORD}){_JOINER}verse\s+({_NUM_OR_WORD})\b",
    re.IGNORECASE,
)
_SPOKEN_FORM_NO_CHAPTER = re.compile(
    rf"\b({_BOOK_RE})\s+(\d{{1,3}}){_JOINER}verse\s+({_NUM_OR_WORD})\b",
    re.IGNORECASE,
)

# Verse ranges: "John chapter 3 verses 16 through 18" / "...16 to 18" /
# "...16-18". Requires an explicit chapter (via "chapter N") in the same
# utterance -- a bare-context range ("verses 16 through 18" alone) is
# handled separately by _BARE_VERSE_RANGE against confirmed context.
_RANGE_JOIN = r"(?:through|to|-)"
_SPOKEN_RANGE = re.compile(
    rf"\b({_BOOK_RE})\s+chapter\s+({_NUM_OR_WORD}){_JOINER}verses\s+({_NUM_OR_WORD})\s*{_RANGE_JOIN}\s*({_NUM_OR_WORD})\b",
    re.IGNORECASE,
)
_SPOKEN_RANGE_NO_CHAPTER = re.compile(
    rf"\b({_BOOK_RE})\s+(\d{{1,3}}){_JOINER}verses\s+({_NUM_OR_WORD})\s*{_RANGE_JOIN}\s*({_NUM_OR_WORD})\b",
    re.IGNORECASE,
)
_BARE_VERSE_RANGE = re.compile(
    rf"\bverses\s+({_NUM_OR_WORD})\s*{_RANGE_JOIN}\s*({_NUM_OR_WORD})\b(?=[\s,.!?]|$)",
    re.IGNORECASE,
)

# Dangling "Book chapter N verse" with NOTHING after "verse" -- the speaker
# got cut off (interrupted, paused mid-thought) before saying the verse
# number. Only matches when "verse" is the literal last word in the chunk;
# if a number followed it, _SPOKEN_FORM above would already have matched
# it first. Without this, "Romans chapter 8 verse" silently drops the
# chapter entirely (matches neither _SPOKEN_FORM, which needs a verse
# number, nor _CHAPTER_ONLY, which deliberately refuses to match when
# "verse" trails it) -- so a later bare "verse one" has nothing to confirm
# against and falls back to whatever stale context was last confirmed.
_DANGLING_CHAPTER_VERSE = re.compile(
    rf"\b({_BOOK_RE})\s+chapter\s+({_NUM_OR_WORD}){_JOINER}verse\s*$",
    re.IGNORECASE,
)

_CHAPTER_ONLY = re.compile(
    rf"\b({_BOOK_RE})\s+chapter\s+({_NUM_OR_WORD})\b(?!\s*{_JOINER.strip()}\s*verse)",
    re.IGNORECASE,
)

# Book-only priming: "turn to Romans", "turn in your bible(s) to Romans",
# "go to Romans", "open to Romans". Explicit-phrase-gated on purpose -- a
# bare book-name mention elsewhere in a sentence must NOT reset context.
_BOOK_ONLY = re.compile(
    rf"\b(?:turn(?:\s+in\s+your\s+bibles?)?\s+to|go\s+to|open\s+to|open\s+your\s+bibles?\s+to)\s+"
    rf"({_BOOK_RE})\b(?!\s*[\d:.]|\s+chapter)",
    re.IGNORECASE,
)

# "book of John", "in the book of Romans" — common spoken lead-in before
# a chapter/verse reference, often split across STT chunks.
_BOOK_OF = re.compile(
    rf"\b(?:in\s+the\s+)?book\s+of\s+({_BOOK_RE})\b(?!\s*[\d:.]|\s+chapter)",
    re.IGNORECASE,
)

_BARE_VERSE = re.compile(
    rf"\bverse\s+({_NUM_OR_WORD})\b(?=[\s,.!?]|$)",
    re.IGNORECASE,
)

# Bare chapter number, no book name: "chapter 8" said as a follow-up after
# a book-only prime ("turn to Romans" ... "chapter 8"). Only consulted when
# context already has a book (see step 4c) -- otherwise meaningless.
_BARE_CHAPTER = re.compile(
    rf"\bchapter\s+({_NUM_OR_WORD})\b(?!\s*{_JOINER.strip()}\s*verse)",
    re.IGNORECASE,
)

# Bare chapter+verse when the book is already known from context — covers
# STT splits like "turn to John" / "chapter 3 verse 16".
_BARE_CHAPTER_VERSE = re.compile(
    rf"\bchapter\s+({_NUM_OR_WORD}){_JOINER}verse\s+({_NUM_OR_WORD})\b",
    re.IGNORECASE,
)

# "Genesis 13" -- a single bare number after a book name, with no second
# number following and no "chapter"/"verse" keyword. Genuinely ambiguous
# in isolation. Only fires when nothing with two numbers or a range
# matched first (checked after those patterns), so it never steals a
# match from "Genesis 13:14" or a verse-range utterance.
_BOOK_SINGLE_NUMBER = re.compile(
    rf"\b({_BOOK_RE})\s+({_NUM_OR_WORD})\b"
    rf"(?!\s*[:./\-]?\s*(?:{_NUM_OR_WORD})\b)",
    re.IGNORECASE,
)

_BOOK_TWO_NUMBERS = re.compile(
    rf"\b({_BOOK_RE})\s+(\d{{1,3}})\s+(\d{{1,3}})\b(?!\s*[:./])",
    re.IGNORECASE,
)

# Spoken numbers only — "john three sixteen", "romans eight twenty eight"
_SPOKEN_NUMBERS_FULL = re.compile(
    rf"\b({_BOOK_RE})\s+({_NUMWORD})\s+({_NUMWORD})\b",
    re.IGNORECASE,
)


def _last_match(pattern: re.Pattern, text: str) -> re.Match | None:
    """
    Return the LAST (rightmost/most-recent) match instead of re.search's
    first match.

    Why this matters: detection often runs against a merged buffer of the
    previous chunk + the current chunk (to catch references split across
    chunk boundaries). If the previous chunk already contained a complete
    reference and the current chunk contains a NEW one, the old reference
    sits earlier in the string. re.search stops at the first match, so it
    would silently re-detect the stale reference and never even look at
    the new one. Always preferring the last match makes "most recently
    spoken" win, whether that's a repeat of the same verse or a brand new
    one -- and it costs nothing when there's only one match.
    """
    last = None
    for last in pattern.finditer(text):
        pass
    return last


def _resolve_ambiguous_number(bible_db, book_number: int, number: int) -> tuple[int, int] | None:
    """Only called when `number` taken whole as a chapter guess is already
    known to be out of range for this book (e.g. "1 Corinthians 316" --
    that book only has 16 chapters). Tries splitting the digits into
    chapter+verse (e.g. 316 -> 3:16, or 31:6) and validates each split
    against the book's REAL chapter/verse ranges via bible_db.

    Returns (chapter, verse) only when EXACTLY ONE split validates -- safe
    to auto-fire on. Returns None when zero splits validate (nothing safe
    to fire; caller keeps the old prime-and-wait behavior) or when 2+
    splits validate (genuine ambiguity -- guessing which one risks
    confidently returning the WRONG verse, so this is treated the same as
    any other unresolved reference: prime and wait for the person to say
    'verse N' or a full explicit form)."""
    if bible_db is None:
        return None
    digits = str(number)
    if len(digits) < 2:
        return None
    valid_splits = []
    for i in range(1, len(digits)):
        chapter_part, verse_part = digits[:i], digits[i:]
        try:
            chapter, verse = int(chapter_part), int(verse_part)
        except ValueError:
            continue
        if chapter < 1 or verse < 1:
            continue
        if bible_db.validate_reference(book_number, chapter, verse).get("valid"):
            valid_splits.append((chapter, verse))
    if len(valid_splits) == 1:
        return valid_splits[0]
    return None


def detect_direct_reference(
    text: str, context: ReferenceContext, bible_db=None,
    regex_threshold: float = 0.75,
) -> dict | None:
    """
    Run all detection patterns against transcript text, priority order.
    Updates context whenever a book+chapter is resolved so bare 'verse N'
    works later. Returns a result dict or None.

    Within each pattern type, the LAST (most recent) match in the text
    wins -- see _last_match -- so stale references left over from a merged
    multi-chunk buffer never shadow a newer one.

    bible_db: optional. When provided, enables the digit-split fallback
    for an out-of-range bare-number guess (see _resolve_ambiguous_number).
    When None, that step is skipped and behavior is unchanged.

    regex_threshold: 0-1 scale, injected from config.ini [detection]
    regex_threshold (see app_config.py) -- floor for the fuzzy book-name
    matcher used as a last-resort fallback in _fuzzy_detect. Previously
    hardcoded to 70 (on rapidfuzz's 0-100 scale) inline; now converted
    from this single config-driven value so it can't drift from what
    config.ini documents.
    """
    if not text or not text.strip():
        return None

    # A pending guess that has silently expired since the last call falls
    # back to chapter-only BEFORE this chunk's own patterns run, so it
    # never lingers past its timeout and doesn't shadow fresh detection.
    context.check_pending_timeout()

    # Normalize spoken prefixes (ordinal AND cardinal) before any matching
    text_norm = _normalize_prefixes(text.strip())
    text_norm = _normalize_stt_artifacts(text_norm)
    text_norm = apply_stt_book_aliases(text_norm)

    # 1) Standard notation: "John 3:16"
    m = _last_match(_STANDARD_NOTATION, text_norm)
    if m:
        book_raw, chap_raw, verse_raw = m.groups()
        key = book_raw.lower()
        if key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            chapter, verse = int(chap_raw), int(verse_raw)
            context.discard_pending("explicit standard-notation reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, verse, 0.97, m.group(0))

    # 2) Spoken verse range WITH explicit chapter: "John chapter 3 verses 16 through 18"
    m = _last_match(_SPOKEN_RANGE, text_norm)
    if m:
        book_raw, chap_raw, v1_raw, v2_raw = m.groups()
        chapter = _parse_number_token(chap_raw)
        v1, v2 = _parse_number_token(v1_raw), _parse_number_token(v2_raw)
        key = book_raw.lower()
        if chapter and v1 and v2 and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("explicit verse-range reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, min(v1, v2), 0.95,
                            m.group(0), verse_end=max(v1, v2))

    # 2b) Spoken verse range, no 'chapter' keyword: "Psalm 23 verses 1 to 3"
    m = _last_match(_SPOKEN_RANGE_NO_CHAPTER, text_norm)
    if m:
        book_raw, chap_raw, v1_raw, v2_raw = m.groups()
        chapter = _parse_number_token(chap_raw)
        v1, v2 = _parse_number_token(v1_raw), _parse_number_token(v2_raw)
        key = book_raw.lower()
        if chapter and v1 and v2 and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("explicit verse-range reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, min(v1, v2), 0.95,
                            m.group(0), verse_end=max(v1, v2))

    # 3) Spoken form (+ optional "and"): "Romans chapter 8 verse 28" / "...and verse 28"
    m = _last_match(_SPOKEN_FORM, text_norm)
    if m:
        book_raw, chap_raw, verse_raw = m.groups()
        chapter = _parse_number_token(chap_raw)
        verse   = _parse_number_token(verse_raw)
        key = book_raw.lower()
        if chapter and verse and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("explicit spoken-form reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, verse, 0.95, m.group(0))

    # 3b) Spoken form no 'chapter' keyword: "Psalm 23 verse 1"
    m = _last_match(_SPOKEN_FORM_NO_CHAPTER, text_norm)
    if m:
        book_raw, chap_raw, verse_raw = m.groups()
        chapter = _parse_number_token(chap_raw)
        verse   = _parse_number_token(verse_raw)
        key = book_raw.lower()
        if chapter and verse and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            if chapter >= 10 and len(str(chapter)) == 2:
                d0, d1 = int(str(chapter)[0]), int(str(chapter)[1])
                if verse == d1 and bible_db and bible_db.validate_reference(
                    book_number, d0, d1
                ).get("valid"):
                    chapter, verse = d0, d1
            context.discard_pending("explicit spoken-form reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, verse, 0.95, m.group(0))

    # 3d) "John 1 1" — two adjacent numbers, no chapter/verse keywords
    m = _last_match(_BOOK_TWO_NUMBERS, text_norm)
    if m:
        book_raw, c_raw, v_raw = m.groups()
        chapter = _parse_number_token(c_raw)
        verse = _parse_number_token(v_raw)
        key = book_raw.lower()
        if chapter and verse and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("book N N reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, verse, 0.94, m.group(0))

    # 3c) Dangling "Book chapter N verse"
    # number hasn't been spoken yet (still coming, or the speaker was cut
    # off). Primes a pending guess on the chapter instead of dropping it,
    # so a later bare "verse N" confirms against THIS chapter rather than
    # falling back to stale prior context. Reaching here means steps 3/3b
    # already failed to find a verse number, so this really is dangling.
    m = _last_match(_DANGLING_CHAPTER_VERSE, text_norm)
    if m:
        book_raw, chap_raw = m.groups()
        chapter = _parse_number_token(chap_raw)
        key = book_raw.lower()
        if chapter and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            return context.prime_pending(book_number, book_name, chapter)

    # 4) Chapter-only: "James chapter 4" -- confirms context
    m = _last_match(_CHAPTER_ONLY, text_norm)
    if m:
        book_raw, chap_raw = m.groups()
        chapter = _parse_number_token(chap_raw)
        key = book_raw.lower()
        if chapter and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("explicit chapter-only reference matched")
            context.update(book_number, book_name, chapter)

    # 4b) Book-only priming: "turn to Romans" -- book known, chapter not yet
    m = _last_match(_BOOK_ONLY, text_norm)
    if m:
        book_raw = m.group(1)
        key = book_raw.lower()
        if key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("explicit book-only reference matched")
            context.update_book_only(book_number, book_name)

    # 4b2) "book of John" priming — same intent as turn/go/open-to.
    m = _last_match(_BOOK_OF, text_norm)
    if m:
        book_raw = m.group(1)
        key = book_raw.lower()
        if key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("book-of priming matched")
            context.update_book_only(book_number, book_name)

    # 4c) Bare chapter number, no book name: "chapter 8" filling in a
    # book that's already known (from book-only priming, or simply still
    # confirmed from a moment ago) but had no chapter yet.
    m = _last_match(_BARE_CHAPTER, text_norm)
    if m and context.last_book_number is not None:
        chapter = _parse_number_token(m.group(1))
        if chapter:
            context.discard_pending("bare chapter number matched")
            context.update(context.last_book_number, context.last_book, chapter)

    # 4d) Bare chapter+verse when book already known: "chapter 3 verse 16"
    m = _last_match(_BARE_CHAPTER_VERSE, text_norm)
    if m and context.last_book_number is not None:
        chapter = _parse_number_token(m.group(1))
        verse = _parse_number_token(m.group(2))
        if chapter and verse:
            context.discard_pending("bare chapter+verse with book context")
            context.update(context.last_book_number, context.last_book, chapter)
            return _result(
                "regex", context.last_book, context.last_book_number,
                chapter, verse, 0.92, m.group(0),
            )

    # 5) Bare verse RANGE resolved via confirmed context: "verses 16 to 18"
    m = _last_match(_BARE_VERSE_RANGE, text_norm)
    if m:
        v1 = _parse_number_token(m.group(1))
        v2 = _parse_number_token(m.group(2))
        if v1 is not None and v2 is not None:
            resolved = context.resolve_bare_verse(min(v1, v2))
            if resolved:
                return _result(
                    "regex", resolved["book"], resolved["book_number"],
                    resolved["chapter"], resolved["verse"], 0.88, m.group(0),
                    verse_end=max(v1, v2),
                )

    # 6) Single-chapter-book bare number: "Jude 3" -> Jude 1:3, UNAMBIGUOUS,
    #    fires immediately, no pending state (only one chapter exists).
    for m in _BOOK_SINGLE_NUMBER.finditer(text_norm):
        book_raw, num_raw = m.groups()
        key = book_raw.lower()
        if key not in NAME_TO_BOOK:
            continue
        book_number, book_name = NAME_TO_BOOK[key]
        if book_number in SINGLE_CHAPTER_BOOKS:
            verse = _parse_number_token(num_raw)
            if verse:
                context.discard_pending("single-chapter-book reference matched")
                context.update(book_number, book_name, 1)
                return _result("regex", book_name, book_number, 1, verse, 0.93, m.group(0))

    # 7) Multi-chapter bare number: "John 11" -- AMBIGUOUS. Primes a
    #    pending guess instead of assuming chapter. Does NOT return/trigger.
    m = _last_match(_BOOK_SINGLE_NUMBER, text_norm)
    if m:
        book_raw, num_raw = m.groups()
        key = book_raw.lower()
        if key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            chapter_guess = _parse_number_token(num_raw)
            if chapter_guess:
                collapsed = _try_collapsed_chapter_verse(
                    bible_db, book_number, book_name, chapter_guess, text_norm, context,
                )
                if collapsed:
                    chapter, verse = collapsed
                    context.discard_pending("collapsed STT chapter:verse matched")
                    context.update(book_number, book_name, chapter)
                    return _result(
                        "regex", book_name, book_number, chapter, verse, 0.91, m.group(0),
                    )
                # If the whole number is already a plausible chapter for
                # this book, keep the existing behavior untouched (still
                # genuinely ambiguous between "chapter N" and "verse N of
                # the current chapter" -- prime and wait, as always).
                chapter_as_guessed_is_valid = (
                    bible_db is not None
                    and bible_db.validate_reference(book_number, chapter_guess).get("valid")
                )
                if not chapter_as_guessed_is_valid:
                    # The guess is out of range as a bare chapter (e.g.
                    # "1 Corinthians 316" -- that book only has 16
                    # chapters). Try splitting its digits into chapter+
                    # verse and fire immediately, but ONLY if exactly one
                    # split is valid -- see _resolve_ambiguous_number for
                    # why 0 or 2+ valid splits both fall through to the
                    # ordinary prime-and-wait path below instead.
                    split = _resolve_ambiguous_number(bible_db, book_number, chapter_guess)
                    if split is not None:
                        chapter, verse = split
                        context.discard_pending(
                            "digit-split chapter:verse reference matched"
                        )
                        context.update(book_number, book_name, chapter)
                        return _result(
                            "regex", book_name, book_number, chapter, verse, 0.90, m.group(0),
                        )
                # Short-circuit here: this utterance is fully consumed by
                # the prime. Falling through would let the fuzzy fallback
                # below misread it (e.g. its own regex can backtrack-split
                # a single number like "11" into two digits "1"+"1" and
                # fire a false John-1:1-style match on the very ambiguity
                # this pending state exists to avoid guessing at). Return
                # prime_pending's "handled" marker (not bare None) so the
                # caller can tell "consumed" apart from "no match, keep
                # escalating".
                return context.prime_pending(book_number, book_name, chapter_guess)

    # 8) Bare verse: "verse 10" -- try PENDING confirmation first (medium
    #    confidence, tagged), then fall back to confirmed-context resolution.
    m = _last_match(_BARE_VERSE, text_norm)
    if m:
        verse = _parse_number_token(m.group(1))
        if verse is not None:
            confirmed = context.confirm_pending(verse)
            if confirmed:
                return _result(
                    "regex", confirmed["book"], confirmed["book_number"],
                    confirmed["chapter"], confirmed["verse"], 0.78, m.group(0),
                    bare_number_confirmed=True,
                )
            resolved = context.resolve_bare_verse(verse)
            if resolved:
                return _result(
                    "regex", resolved["book"], resolved["book_number"],
                    resolved["chapter"], resolved["verse"], 0.90, m.group(0),
                )

    # 9) Spoken numbers: "john three sixteen"
    m = _last_match(_SPOKEN_NUMBERS_FULL, text_norm)
    if m:
        book_raw, chap_word, verse_word = m.groups()
        chapter = _parse_number_token(chap_word)
        verse   = _parse_number_token(verse_word)
        key = book_raw.lower()
        if chapter and verse and key in NAME_TO_BOOK:
            book_number, book_name = NAME_TO_BOOK[key]
            context.discard_pending("explicit spoken-numbers reference matched")
            context.update(book_number, book_name, chapter)
            return _result("regex", book_name, book_number, chapter, verse, 0.92, m.group(0))

    # 9b) Standalone book name as the entire chunk (common STT split:
    # "John" ... "chapter 3 verse 16"). Only when nothing else matched and
    # the utterance IS just the book name — not embedded in a sentence.
    stripped_key = text_norm.strip().strip(".,;:!?\"'").lower()
    if stripped_key in NAME_TO_BOOK:
        book_number, book_name = NAME_TO_BOOK[stripped_key]
        context.discard_pending("standalone book name primes context")
        context.update_book_only(book_number, book_name)
        return {"triggered": False, "handled": "book_primed", "book": book_name}

    # 10) Fuzzy fallback -- catches mishearing: "genisis", "revelations", "jon"
    return _fuzzy_detect(text_norm, context, regex_threshold=regex_threshold)


def _try_collapsed_chapter_verse(
    bible_db, book_number: int, book_name: str, chapter_guess: int,
    text_norm: str, context: ReferenceContext,
) -> tuple[int, int] | None:
    """STT often collapses 'chapter 1 verse 1' into 'John 11'. Recover when
    'verse' appears in the same utterance and digit-split validates."""
    if chapter_guess < 10 or len(str(chapter_guess)) != 2:
        return None
    if not re.search(r"\bverse\b", text_norm, re.IGNORECASE):
        if not context.has_pending():
            return None
    digits = str(chapter_guess)
    ch, ver = int(digits[0]), int(digits[1])
    if ch < 1 or ver < 1:
        return None
    if bible_db is None:
        return None
    if bible_db.validate_reference(book_number, ch, ver).get("valid"):
        return ch, ver
    return None


def _fuzzy_detect(text: str, context: ReferenceContext, regex_threshold: float = 0.75) -> dict | None:
    """
    V1-style rapidfuzz fuzzy book-name matching. Only runs when all strict
    patterns fail. Tolerates OCR/ASR errors in book names.
    """
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        return None
    # rapidfuzz's scorer is 0-100; config.ini's regex_threshold is 0-1 to
    # stay consistent with every other confidence value in this app.
    score_floor = regex_threshold * 100

    books_lower = {k: k for k in NAME_TO_BOOK}
    books_list  = list(books_lower.keys())

    _spoken_num = r"(\d+|[a-z]+(?:[\s\-][a-z]+){0,2})"
    patterns = [
        # NOTE: the chapter/verse separator here is a MANDATORY colon/dot
        # (not optional+zero-width) or mandatory whitespace -- an optional
        # zero-width separator lets \d+ backtrack and silently split a
        # single bare number like "11" into chapter=1, verse=1, which is
        # exactly the false-positive this whole file's pending-state
        # machine exists to prevent. Never make this separator optional.
        re.compile(r'(.+?)\s+(\d+)\s*[:\.]\s*(\d+)'),        # book chapter:verse / chapter.verse
        re.compile(rf'(.+?)\s+chapter\s+{_spoken_num}\s+verse\s+{_spoken_num}', re.IGNORECASE),
        re.compile(r'(.+?)\s+(\d+)\s+(\d+)'),                # book chapter verse (whitespace-separated)
    ]
    for pattern in patterns:
        best_result = None
        best_start = -1
        for match in pattern.finditer(text):
            groups = match.groups()
            if len(groups) < 3:
                continue
            potential_book = groups[0].strip().lower()
            chap = _parse_number_token(groups[1])
            verse = _parse_number_token(groups[2])
            if not chap or not verse:
                continue
            res = process.extractOne(potential_book, books_list, scorer=fuzz.ratio)
            if res and res[1] >= score_floor and match.start() > best_start:  # config-driven similarity floor
                matched_key = res[0]
                book_number, book_name = NAME_TO_BOOK[matched_key]
                best_start = match.start()
                best_result = (book_number, book_name, chap, verse, groups[0], res[1])
        if best_result:
            book_number, book_name, chap, verse, matched_text, score = best_result
            context.discard_pending("fuzzy-matched reference took priority")
            context.update(book_number, book_name, chap)
            logger.debug("Fuzzy match: '%s' → %s (score=%d)", matched_text, book_name, score)
            return _result("regex", book_name, book_number, chap, verse, 0.78, matched_text)
    return None


def _result(source: str, book: str, book_number: int,
            chapter: int, verse: int, confidence: float,
            matched_text: str, verse_end: int | None = None,
            bare_number_confirmed: bool = False) -> dict:
    result = {
        "source": source,
        "book": book,
        "book_number": book_number,
        "chapter": chapter,
        "verse": verse,
        "confidence": confidence,
        "matched_text": matched_text,
    }
    if verse_end is not None and verse_end != verse:
        result["verse_end"] = verse_end
    if bare_number_confirmed:
        result["bare_number_confirmed"] = True
    return result
