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
# than "next verse please". The label is what the operator sees (and can
# switch off) in Settings — it is the plain-English form of the pattern.
_PHRASES: list[tuple[str, str, float, str]] = [
    (INTENT_NEXT, r"(?:go (?:to )?(?:the )?)?next verse(?: please)?", 0.95, "next verse"),
    (INTENT_NEXT, r"next one(?: please)?", 0.9, "next one"),
    (INTENT_NEXT, r"(?:scroll|move|go) (?:on |ahead )?(?:to the )?next", 0.9, "go to next"),
    (INTENT_NEXT, r"verse after (?:that|this)", 0.9, "verse after that"),
    (INTENT_NEXT, r"continue(?: reading| please)?", 0.85, "continue"),
    (INTENT_NEXT, r"(?:go |carry )?on(?: to the next)?(?: verse)", 0.85, "carry on"),
    (INTENT_NEXT, r"forward(?: one)?(?: verse)?", 0.8, "forward"),
    (INTENT_NEXT, r"next", 0.6, "next"),
    (INTENT_PREV, r"(?:go (?:to )?(?:the )?)?previous verse(?: please)?", 0.95, "previous verse"),
    (INTENT_PREV, r"(?:verse )?before (?:that|this)", 0.9, "before that"),
    (INTENT_PREV, r"(?:go |move )?back (?:one|a) verse", 0.95, "back one verse"),
    (INTENT_PREV, r"(?:go|move) back", 0.75, "go back"),
    (INTENT_PREV, r"(?:go |take us )?back(?: please)?", 0.75, "back"),
    (INTENT_PREV, r"(?:the )?(?:verse|one) before(?: that| this)?", 0.9, "the verse before that"),
    (INTENT_PREV, r"(?:last|previous) verse(?: please)?", 0.95, "last verse"),
    (INTENT_PREV, r"previous(?: one)?", 0.7, "previous"),
    (INTENT_REPEAT, r"(?:say|read) (?:that|it) again", 0.9, "read that again"),
    (INTENT_REPEAT, r"repeat (?:that|the verse|it)", 0.9, "repeat that"),
    (INTENT_REPEAT, r"(?:same|that) verse again", 0.9, "that verse again"),
    (INTENT_CLEAR, r"(?:clear|hide) (?:the )?(?:screen|verse|slide)", 0.95, "clear the screen"),
    (INTENT_CLEAR, r"take (?:it|that) (?:down|off)", 0.9, "take it down"),
    (INTENT_CLEAR, r"blank (?:the )?screen", 0.95, "blank screen"),
    (INTENT_BROADCAST, r"(?:put|bring) (?:it|that) (?:up(?: on(?: the)? screen)?|on(?: the)? screen)", 0.9, "put it on screen"),
    (INTENT_BROADCAST, r"(?:show|display) (?:it|that|the verse)(?: (?:up|now|please))?", 0.9, "show that"),
    (INTENT_BROADCAST, r"(?:go|put us) live(?: with (?:it|that))?", 0.85, "go live"),
]

_COMPILED = [
    (intent, re.compile(rf"^{pattern}$"), score, label)
    for intent, pattern, score, label in _PHRASES
]

INTENTS = (INTENT_NEXT, INTENT_PREV, INTENT_REPEAT, INTENT_CLEAR, INTENT_BROADCAST)


def builtin_keywords() -> dict[str, list[str]]:
    """The stock phrase labels per intent, for the Settings keyword editor."""
    out: dict[str, list[str]] = {intent: [] for intent in INTENTS}
    for intent, _pattern, _score, label in _PHRASES:
        out.setdefault(intent, []).append(label)
    return out

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

    def __init__(
        self,
        cooldown_seconds: float = COMMAND_COOLDOWN_SECONDS,
        disabled_keywords: Optional[list[str]] = None,
        custom_keywords: Optional[dict[str, list[str]]] = None,
    ):
        self.cooldown_seconds = cooldown_seconds
        self._last_fired_at = 0.0
        self._last_intent: Optional[str] = None
        self._disabled: set[str] = set()
        self._custom: dict[str, list[str]] = {}
        self.set_keywords(disabled_keywords, custom_keywords)

    def set_keywords(
        self,
        disabled_keywords: Optional[list[str]] = None,
        custom_keywords: Optional[dict[str, list[str]]] = None,
    ) -> None:
        """Operator-tuned vocabulary: switch stock phrases off, add own ones.
        Custom phrases are matched literally (whole clause), so a badly
        chosen one can't turn into a runaway regex."""
        self._disabled = {_normalize(k) for k in (disabled_keywords or []) if k}
        self._custom = {}
        for intent, phrases in (custom_keywords or {}).items():
            if intent not in INTENTS:
                continue
            cleaned = [_normalize(p) for p in phrases or [] if _normalize(p)]
            if cleaned:
                self._custom[intent] = cleaned

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
            for intent, custom_phrases in self._custom.items():
                if candidate not in custom_phrases:
                    continue
                if intent in (INTENT_NEXT, INTENT_PREV) and context.get("has_verse") is False:
                    continue
                if best is None or 0.95 > best.confidence:
                    best = VoiceCommand(intent=intent, confidence=0.95, matched_phrase=candidate)
            for intent, pattern, score, label in _COMPILED:
                if _normalize(label) in self._disabled:
                    continue
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
