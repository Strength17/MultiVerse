"""
bible_books.py

Canonical book list with common abbreviations, used by verse_detector.py
for direct-reference regex matching. Multiples-of-10 numbering kept
consistent with WindowVerse's existing schema (per the original README's
bible_db.py / data/NKJV.SQLite3 convention).

IMPORTANT -- this app detects references from SPOKEN transcripts, never
typed text. Abbreviations here should only be things a person would
plausibly SAY as a shorthand book name ("Rev" for Revelation). They must
NOT include ordinary standalone English words, even if that word is also
a legitimate written abbreviation in print Bible references (e.g. "Is."
for Isaiah, "Am." for Amos) -- WinRT will transcribe someone saying the
word "is" as "is", and every one of those got silently treated as a
reference to Isaiah until this was caught (see _COMMON_WORD_GUARD below,
which fails loudly if this regresses).
"""

# (book_number, canonical_name, [abbreviations...])
BOOKS = [
    (10, "Genesis", ["gen", "ge", "gn"]),
    (20, "Exodus", ["exo", "ex", "exod"]),
    (30, "Leviticus", ["lev", "le", "lv"]),
    (40, "Numbers", ["num", "nu", "nm", "nb"]),
    (50, "Deuteronomy", ["deut", "dt", "de"]),
    (60, "Joshua", ["josh", "jos", "jsh"]),
    (70, "Judges", ["judg", "jdg", "jg"]),
    (80, "Ruth", ["rut", "ru"]),
    (90, "1 Samuel", ["1sam", "1sa", "1 sam", "first samuel"]),
    (100, "2 Samuel", ["2sam", "2sa", "2 sam", "second samuel"]),
    (110, "1 Kings", ["1kgs", "1ki", "1 kings", "first kings"]),
    (120, "2 Kings", ["2kgs", "2ki", "2 kings", "second kings"]),
    (130, "1 Chronicles", ["1chr", "1ch", "1 chron", "first chronicles"]),
    (140, "2 Chronicles", ["2chr", "2ch", "2 chron", "second chronicles"]),
    (150, "Ezra", ["ezr", "ez"]),
    (160, "Nehemiah", ["neh", "ne"]),
    (170, "Esther", ["esth", "est", "es"]),
    (180, "Job", ["jb"]),
    (190, "Psalms", ["psa", "ps", "psalm", "pslm"]),
    (200, "Proverbs", ["prov", "pro", "prv"]),
    (210, "Ecclesiastes", ["eccl", "ecc", "ec"]),
    (220, "Song of Solomon", ["song", "sos", "song of songs"]),
    (230, "Isaiah", ["isa"]),
    (240, "Jeremiah", ["jer", "je"]),
    (250, "Lamentations", ["lam", "la"]),
    (260, "Ezekiel", ["ezek", "eze", "ezk"]),
    (270, "Daniel", ["dan", "da", "dn"]),
    (280, "Hosea", ["hos", "ho"]),
    (290, "Joel", ["joe", "jl"]),
    (300, "Amos", ["amo"]),
    (310, "Obadiah", ["obad", "oba", "ob"]),
    (320, "Jonah", ["jon", "jnh"]),
    (330, "Micah", ["mic", "mi"]),
    (340, "Nahum", ["nah", "na"]),
    (350, "Habakkuk", ["hab", "hb"]),
    (360, "Zephaniah", ["zeph", "zep", "zp"]),
    (370, "Haggai", ["hag", "hg"]),
    (380, "Zechariah", ["zech", "zec", "zc"]),
    (390, "Malachi", ["mal", "ml"]),
    (400, "Matthew", ["matt", "mat", "mt"]),
    (410, "Mark", ["mrk", "mk", "mr"]),
    (420, "Luke", ["luk", "lk"]),
    (430, "John", ["jhn", "jn"]),
    (440, "Acts", ["act", "ac"]),
    (450, "Romans", ["rom", "ro", "rm"]),
    (460, "1 Corinthians", ["1cor", "1co", "first corinthians"]),
    (470, "2 Corinthians", ["2cor", "2co", "second corinthians"]),
    (480, "Galatians", ["gal", "ga"]),
    (490, "Ephesians", ["eph", "ephes"]),
    (500, "Philippians", ["phil", "php", "pp"]),
    (510, "Colossians", ["col", "co"]),
    (520, "1 Thessalonians", ["1thess", "1th", "first thessalonians"]),
    (530, "2 Thessalonians", ["2thess", "2th", "second thessalonians"]),
    (540, "1 Timothy", ["1tim", "1ti", "first timothy"]),
    (550, "2 Timothy", ["2tim", "2ti", "second timothy"]),
    (560, "Titus", ["tit", "ti"]),
    (570, "Philemon", ["philem", "phm", "pm"]),
    (580, "Hebrews", ["heb"]),
    (590, "James", ["jas", "jm"]),
    (600, "1 Peter", ["1pet", "1pe", "first peter"]),
    (610, "2 Peter", ["2pet", "2pe", "second peter"]),
    (620, "1 John", ["1jn", "1jo", "first john"]),
    (630, "2 John", ["2jn", "2jo", "second john"]),
    (640, "3 John", ["3jn", "3jo", "third john"]),
    (650, "Jude", ["jud", "jd"]),
    (660, "Revelation", ["rev", "re", "revelations"]),
]

# French book names (Louis Segond) keyed by canonical English name.
FRENCH_BOOK_NAMES: dict[str, str] = {
    "Genesis": "Genèse",
    "Exodus": "Exode",
    "Leviticus": "Lévitique",
    "Numbers": "Nombres",
    "Deuteronomy": "Deutéronome",
    "Joshua": "Josué",
    "Judges": "Juges",
    "Ruth": "Ruth",
    "1 Samuel": "1 Samuel",
    "2 Samuel": "2 Samuel",
    "1 Kings": "1 Rois",
    "2 Kings": "2 Rois",
    "1 Chronicles": "1 Chroniques",
    "2 Chronicles": "2 Chroniques",
    "Ezra": "Esdras",
    "Nehemiah": "Néhémie",
    "Esther": "Esther",
    "Job": "Job",
    "Psalms": "Psaumes",
    "Proverbs": "Proverbes",
    "Ecclesiastes": "Ecclésiaste",
    "Song of Solomon": "Cantique des Cantiques",
    "Isaiah": "Ésaïe",
    "Jeremiah": "Jérémie",
    "Lamentations": "Lamentations",
    "Ezekiel": "Ézéchiel",
    "Daniel": "Daniel",
    "Hosea": "Osée",
    "Joel": "Joël",
    "Amos": "Amos",
    "Obadiah": "Abdias",
    "Jonah": "Jonas",
    "Micah": "Michée",
    "Nahum": "Nahum",
    "Habakkuk": "Habakuk",
    "Zephaniah": "Sophonie",
    "Haggai": "Aggée",
    "Zechariah": "Zacharie",
    "Malachi": "Malachie",
    "Matthew": "Matthieu",
    "Mark": "Marc",
    "Luke": "Luc",
    "John": "Jean",
    "Acts": "Actes",
    "Romans": "Romains",
    "1 Corinthians": "1 Corinthiens",
    "2 Corinthians": "2 Corinthiens",
    "Galatians": "Galates",
    "Ephesians": "Éphésiens",
    "Philippians": "Philippiens",
    "Colossians": "Colossiens",
    "1 Thessalonians": "1 Thessaloniciens",
    "2 Thessalonians": "2 Thessaloniciens",
    "1 Timothy": "1 Timothée",
    "2 Timothy": "2 Timothée",
    "Titus": "Tite",
    "Philemon": "Philémon",
    "Hebrews": "Hébreux",
    "James": "Jacques",
    "1 Peter": "1 Pierre",
    "2 Peter": "2 Pierre",
    "1 John": "1 Jean",
    "2 John": "2 Jean",
    "3 John": "3 Jean",
    "Jude": "Jude",
    "Revelation": "Apocalypse",
}


# Matthew (400) is the first NT book in this schema (multiples of 10).
NT_FIRST_BOOK_NUMBER = 400


def book_testament(book_number: int) -> str:
    """Return ``OT`` or ``NT`` for canonical Protestant ordering."""
    return "NT" if int(book_number) >= NT_FIRST_BOOK_NUMBER else "OT"


def testament_matches(book_number: int, testament_filter: str) -> bool:
    """True when *book_number* passes ``all`` / ``ot`` / ``nt`` filter."""
    filt = (testament_filter or "all").strip().lower()
    if filt in ("", "all"):
        return True
    t = book_testament(book_number).lower()
    return t == filt or (filt == "old" and t == "ot") or (filt == "new" and t == "nt")


def french_book_name(english_name: str) -> str:
    return FRENCH_BOOK_NAMES.get(english_name, english_name)

NAME_TO_BOOK: dict[str, tuple[int, str]] = {}
for num, name, abbrevs in BOOKS:
    NAME_TO_BOOK[name.lower()] = (num, name)
    for a in abbrevs:
        NAME_TO_BOOK[a.lower()] = (num, name)

# ── Guard against the "is" -> Isaiah class of bug ──────────────────────────
# An abbreviation that's also a common standalone spoken English word will
# silently hijack every ordinary sentence containing that word ("where IS
# 1" primed a false Isaiah 1 guess). Kept as a small local list (not
# imported from vocab_correction.py's stopword set) to avoid a circular
# import -- vocab_correction.py imports BOOKS from this file. This is a
# deliberately blunt net, not exhaustive: it exists so the NEXT accidental
# common-word abbreviation someone adds fails fast at import time instead
# of silently misfiring live, months later, exactly like this one did.
_COMMON_SPOKEN_WORDS = frozenset({
    "i", "a", "an", "the", "is", "in", "on", "to", "of", "and", "or", "but",
    "he", "she", "it", "we", "you", "they", "them", "his", "her", "its",
    "so", "as", "at", "by", "for", "if", "me", "my", "no", "not", "now",
    "up", "us", "am", "be", "do", "go", "how", "who", "why", "yes", "was",
    "are", "were", "had", "has", "have", "this", "that", "these", "those",
})
for _num, _name, _abbrevs in BOOKS:
    _bad = _COMMON_SPOKEN_WORDS.intersection(a.lower() for a in _abbrevs)
    if _bad:
        raise ValueError(
            f"bible_books.py: abbreviation(s) {sorted(_bad)} for {_name!r} "
            f"are common spoken English words -- they will false-positive "
            f"on ordinary sentences. Remove them from BOOKS."
        )

# Sorted longest-name-first so regex alternation prefers "1 corinthians"
# over accidentally matching a shorter substring first.
ALL_NAMES_SORTED = sorted(NAME_TO_BOOK.keys(), key=len, reverse=True)

# Reverse lookup: book_number -> canonical name (needed by bible_db.py fallback)
BOOK_NUMBER_TO_CANONICAL: dict[int, str] = {num: name for num, name, _ in BOOKS}

# Canonical name -> book_number (needed by bible_db.py when a DB stores
# book names as strings instead of numbers)
CANONICAL_TO_BOOK_NUMBER: dict[str, int] = {name: num for num, name, _ in BOOKS}

# Short label for the Scripture Browser's book tiles ("1 Samuel" -> "1 Sam").
BOOK_NUMBER_TO_ABBREV: dict[int, str] = {
    num: (abbrevs[0].title() if abbrevs else name[:3]).replace("1", "1 ").replace("2", "2 ").replace("3", "3 ")
    for num, name, abbrevs in BOOKS
}

# Single-chapter books: a bare "Book N" utterance for these is UNAMBIGUOUS
# -- there's only one chapter, so N can only be a verse number. No pending
# state needed; verse_detector fires immediately (chapter=1, verse=N).
SINGLE_CHAPTER_BOOKS: set[int] = {
    310,  # Obadiah
    570,  # Philemon
    630,  # 2 John
    640,  # 3 John
    650,  # Jude
}

# Ordinal-word book stems: books whose canonical/abbrev names start with a
# digit prefix (1/2/3) also get spoken as "first/second/third X" OR as the
# bare cardinal "one/two/three X" (STT artifact, e.g. WinRT emitting "one
# corinthians" instead of "first corinthians"). Scoped to only these stems
# so "one" / "two" / "three" elsewhere in a sentence are never touched.
ORDINAL_BOOK_STEMS = [
    "samuel", "kings", "chronicles", "corinthians", "thessalonians",
    "timothy", "peter", "john",
]

# High-confidence WinRT mishears — applied only when the next token signals
# a Bible reference (chapter / verse / digit), so ordinary English like
# "a romance story" is never rewritten.
STT_BOOK_ALIASES: dict[str, str] = {
    "romance": "Romans",
    "ecclesiastics": "Ecclesiastes",
    "ecclesiastic": "Ecclesiastes",
    "revelations": "Revelation",
    "genisis": "Genesis",
    "mathew": "Matthew",
}

_REF_SIGNAL_WORDS = frozenset({
    "chapter", "chapters", "ch", "ch.", "verse", "verses", "ver", "ver.",
})


def is_reference_signal(token: str) -> bool:
    """True when a token plausibly continues a spoken Bible reference."""
    if not token:
        return False
    t = token.lower().strip(".,;:!?\"'")
    if t in _REF_SIGNAL_WORDS:
        return True
    if t.isdigit():
        return True
    return False


def resolve_stt_book_alias(token: str, next_token: str | None = None) -> str | None:
    """Return canonical book name for a known STT mishear, or None."""
    key = token.lower().strip(".,;:!?\"'")
    canonical = STT_BOOK_ALIASES.get(key)
    if not canonical:
        return None
    if next_token is None or is_reference_signal(next_token):
        return canonical
    return None


def apply_stt_book_aliases(text: str) -> str:
    """Rewrite known misheard book tokens when followed by reference signal."""
    words = text.split()
    if not words:
        return text
    out: list[str] = []
    for i, word in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        alias = resolve_stt_book_alias(word, nxt)
        out.append(alias if alias else word)
    return " ".join(out)
