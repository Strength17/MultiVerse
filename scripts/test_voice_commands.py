"""Voice navigation parsing — commands fire, ordinary preaching doesn't."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_commands import VoiceCommandParser

COMMANDS = [
    ("next verse", "next"),
    ("Next verse, please.", "next"),
    ("next", "next"),
    ("go to the next verse", "next"),
    ("previous verse", "prev"),
    ("go back one verse", "prev"),
    ("read that again", "repeat"),
    ("repeat the verse", "repeat"),
    ("clear the screen", "clear"),
    ("take it down", "clear"),
    ("put it up on screen", "broadcast"),
    ("show that", "broadcast"),
]

# Real sermon speech that must never move the congregation's screen.
NON_COMMANDS = [
    "the next thing I want to say is that God is faithful",
    "let me show you what happened next in the story",
    "next week we will be looking at the book of Acts",
    "and he went back to his father",
    "I want to clear something up before we continue",
    "he displayed his glory",
    "turn with me to the next chapter of your life",
    "",
    "amen",
]

# A book name in the utterance means "look this reference up", never
# "step one verse forward from wherever we happen to be".
REFERENCE_LIKE = [
    "next verse in John",
    "go to the next verse in Romans chapter 8",
    "previous verse in Psalms",
]


def fresh(t: float = 0.0):
    parser = VoiceCommandParser()
    return parser


def main() -> None:
    clock = 100.0
    for text, expected in COMMANDS:
        parser = fresh()
        cmd = parser.parse(text, {"now": clock, "finalized": True, "has_verse": True})
        assert cmd is not None, f"expected a command for {text!r}"
        assert cmd.intent == expected, f"{text!r} -> {cmd.intent}, expected {expected}"
    print(f"OK: {len(COMMANDS)} command phrases recognised")

    for text in NON_COMMANDS:
        parser = fresh()
        cmd = parser.parse(text, {"now": clock, "finalized": True, "has_verse": True})
        assert cmd is None, f"false positive on {text!r} -> {cmd}"
    print(f"OK: {len(NON_COMMANDS)} ordinary phrases ignored")

    for text in REFERENCE_LIKE:
        parser = fresh()
        assert parser.parse(text, {"now": clock, "finalized": True, "has_verse": True}) is None, text
    print(f"OK: {len(REFERENCE_LIKE)} reference-bearing phrases left to detection")

    # Bare next/prev need something on screen to step from.
    parser = fresh()
    assert parser.parse("next", {"now": clock, "finalized": True, "has_verse": False}) is None
    print("OK: bare 'next' ignored with nothing on air")

    # Interim (non-finalized) text never commands.
    parser = fresh()
    assert parser.parse("next verse", {"now": clock, "finalized": False, "has_verse": True}) is None
    print("OK: interim text ignored")

    # Cooldown suppresses dictation's duplicate finalization.
    parser = fresh()
    assert parser.parse("next verse", {"now": 10.0, "finalized": True, "has_verse": True})
    assert parser.parse("next verse", {"now": 10.3, "finalized": True, "has_verse": True}) is None
    assert parser.parse("next verse", {"now": 11.5, "finalized": True, "has_verse": True})
    print("OK: 800ms cooldown")

    print("\nAll voice command checks passed.")


if __name__ == "__main__":
    main()
