"""Gates to skip detection on non-English interpreter speech."""
from __future__ import annotations

import re

_FRENCH_HINTS = re.compile(
    r"\b(le|la|les|un|une|des|de|du|dans|que|qui|est|sont|dieu|seigneur|"
    r"car|pour|avec|sur|notre|vous|nous|ils|elle|ce|cette|comme|mais|ou|"
    r"au|aux|en|par|je|tu|il|mon|ton|son|leur|tout|tous|très|aussi)\b",
    re.IGNORECASE,
)
_REFERENCE_SIGNAL = re.compile(
    r"\b(chapter|chapters|verse|verses|genesis|exodus|leviticus|numbers|"
    r"deuteronomy|joshua|judges|ruth|samuel|kings|chronicles|ezra|nehemiah|"
    r"esther|job|psalm|psalms|proverbs|ecclesiastes|song|isaiah|jeremiah|"
    r"lamenations|ezekiel|daniel|hosea|joel|amos|obadiah|jonah|micah|nahum|"
    r"habakkuk|zephaniah|haggai|zechariah|malachi|matthew|mark|luke|john|"
    r"acts|romans|corinthians|galatians|ephesians|philippians|colossians|"
    r"thessalonians|timothy|titus|philemon|hebrews|james|peter|jude|revelation|"
    r"turn to|open to|go to)\b|\d",
    re.IGNORECASE,
)


def has_reference_signal(text: str) -> bool:
    return bool(_REFERENCE_SIGNAL.search(text or ""))


def looks_like_french_speech(text: str) -> bool:
    if not text or not text.strip():
        return False
    if has_reference_signal(text):
        return False
    words = text.lower().split()
    if len(words) < 2:
        return False
    french_hits = len(_FRENCH_HINTS.findall(text))
    return french_hits >= 2 or french_hits / max(len(words), 1) >= 0.25


def should_skip_detection(text: str) -> bool:
    return looks_like_french_speech(text)
