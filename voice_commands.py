"""
voice_commands.py

Spoken navigation ("next verse", "go back", "show that") parsed out of the
finalized dictation stream before it reaches verse detection.

The whole design problem here is false positives: a preacher says "next"
and "show" constantly in ordinary speech, and reacting to those would
yank the congregation's screen mid-sentence. So this parser is
deliberately conservative:

* a command has to be the WHOLE finalized chunk (or the whole trailing
  clause of it) — "the next thing I want to say" never matches;
* anything containing a book name is left alone, because "next verse in
  John" is a reference lookup, not a sequential step;
* a cooldown suppresses the double-fire you get when Windows dictation
  finalizes the same short utterance twice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from bible_books import NAME_TO_BOOK

# Intents the server knows how to act on.
INTENT_NEXT = "next"
INTENT_PREV = "prev"
INTENT_REPEAT = "repeat"
INTENT_CLEAR = "clear"
INTENT_BROADCAST = "broadcast"

COMMAND_COOLDOWN_SECONDS = 0.8

# Each phrase is matched against a whole clause. Longer/more explicit
# phrasings score higher, so a bare "next" can be treated more cautiously
# than "next verse please".
_PHRASES: list[tuple[str, str, float]] = [
    (INTENT_NEXT, r"(?:go (?:to )?(?:the )?)?next verse(?: please)?", 0.95),
    (INTENT_NEXT, r"next one(?: please)?", 0.9),
    (INTENT_NEXT, r"(?:scroll|move|go) (?:on |ahead )?(?:to the )?next", 0.9),
    (INTENT_NEXT, r"verse after (?:that|this)", 0.9),
    (INTENT_NEXT, r"continue(?: reading| please)?", 0.85),
    (INTENT_NEXT, r"(?:go |carry )?on(?: to the next)?(?: verse)", 0.85),
    (INTENT_NEXT, r"forward(?: one)?(?: verse)?", 0.8),
    (INTENT_NEXT, r"next", 0.6),
    (INTENT_PREV, r"(?:go (?:to )?(?:the )?)?previous verse(?: please)?", 0.95),
    (INTENT_PREV, r"(?:verse )?before (?:that|this)", 0.9),
    (INTENT_PREV, r"(?:go |move )?back (?:one|a) verse", 0.95),
    (INTENT_PREV, r"(?:go|move) back", 0.75),
    (INTENT_PREV, r"(?:go |take us )?back(?: please)?", 0.75),
    (INTENT_PREV, r"(?:the )?(?:verse|one) before(?: that| this)?", 0.9),
    (INTENT_PREV, r"(?:last|previous) verse(?: please)?", 0.95),
    (INTENT_PREV, r"previous(?: one)?", 0.7),
    (INTENT_REPEAT, r"(?:say|read) (?:that|it) again", 0.9),
    (INTENT_REPEAT, r"repeat (?:that|the verse|it)", 0.9),
    (INTENT_REPEAT, r"(?:same|that) verse again", 0.9),
    (INTENT_CLEAR, r"(?:clear|hide) (?:the )?(?:screen|verse|slide)", 0.95),
    (INTENT_CLEAR, r"take (?:it|that) (?:down|off)", 0.9),
    (INTENT_CLEAR, r"blank (?:the )?screen", 0.95),
    (INTENT_BROADCAST, r"(?:put|bring) (?:it|that) (?:up(?: on(?: the)? screen)?|on(?: the)? screen)", 0.9),
    (INTENT_BROADCAST, r"(?:show|display) (?:it|that|the verse)(?: (?:up|now|please))?", 0.9),
    (INTENT_BROADCAST, r"(?:go|put us) live(?: with (?:it|that))?", 0.85),
]

_COMPILED = [(intent, re.compile(rf"^{pattern}$"), score) for intent, pattern, score in _PHRASES]

# Clause boundaries: dictation finalizes on sentence ends, and operators
# tend to tack the command on at the end ("...and that's the point. Next
# verse."). Only the last clause is considered.
_CLAUSE_SPLIT = re.compile(r"[.,;:!?]+")
_PUNCT_STRIP = re.compile(r"[^a-z0-9' ]+")

# A bare "next"/"back" is only trusted when it stands alone as the whole
# utterance — never as the tail of a longer sentence.
_BARE_INTENTS = {INTENT_NEXT: "next", INTENT_PREV: "back"}


@dataclass
class VoiceCommand:
    intent: str
    confidence: float
    matched_phrase: str


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    lowered = _PUNCT_STRIP.sub(" ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def contains_book_name(text: str) -> bool:
    """True when the utterance names a Bible book — those go to reference
    lookup / normal detection, never to sequential navigation."""
    words = _normalize(text).split()
    for size in (3, 2, 1):
        for i in range(len(words) - size + 1):
            candidate = " ".join(words[i:i + size])
            if candidate in NAME_TO_BOOK:
                return True
    return False


class VoiceCommandParser:
    """Stateless apart from the cooldown clock."""

    def __init__(self, cooldown_seconds: float = COMMAND_COOLDOWN_SECONDS):
        self.cooldown_seconds = cooldown_seconds
        self._last_fired_at = 0.0
        self._last_intent: Optional[str] = None

    def parse(self, text: str, context: Optional[dict] = None) -> Optional[VoiceCommand]:
        """Return a command when *text* (a finalized transcript chunk) is a
        navigation instruction, else None.

        context keys (all optional):
          now             — timestamp, for the cooldown
          finalized       — False for interim text; interim never commands
          has_verse       — False when nothing is on air/preview, which makes
                            bare "next"/"back" meaningless and unsafe
        """
        context = context or {}
        if context.get("finalized") is False:
            return None
        normalized = _normalize(text)
        if not normalized:
            return None
        if contains_book_name(normalized):
            return None

        clauses = [c.strip() for c in _CLAUSE_SPLIT.split(_normalize(text)) if c.strip()]
        candidates = [normalized]
        if clauses and clauses[-1] != normalized:
            candidates.append(clauses[-1])

        best: Optional[VoiceCommand] = None
        for index, candidate in enumerate(candidates):
            whole_utterance = index == 0
            for intent, pattern, score in _COMPILED:
                if not pattern.match(candidate):
                    continue
                bare = _BARE_INTENTS.get(intent)
                if bare and len(candidate.split()) <= 2 and not whole_utterance:
                    # "…something something. next" — too weak to act on.
                    continue
                if intent in (INTENT_NEXT, INTENT_PREV) and context.get("has_verse") is False:
                    continue
                if best is None or score > best.confidence:
                    best = VoiceCommand(intent=intent, confidence=score, matched_phrase=candidate)
        if best is None:
            return None

        now = float(context.get("now") or 0.0)
        if now and (now - self._last_fired_at) < self.cooldown_seconds:
            return None
        self._last_fired_at = now
        self._last_intent = best.intent
        return best

    def reset(self) -> None:
        self._last_fired_at = 0.0
        self._last_intent = None
