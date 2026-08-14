"""Canonical verse navigation: boundaries, single-chapter books, gaps.

Builds a synthetic 66-book SQLite file (numbered 1..66, so the DB's own
book-number scheme differs from bible_books.py's 10..660 and the mapping
layer is exercised too) rather than depending on a bundled Bible.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bible_db as bible_db_module
import bible_schema
from bible_books import BOOKS, SINGLE_CHAPTER_BOOKS

# Chapter counts kept small so the fixture stays fast; the handful of books
# the assertions care about get their real shape.
REAL_CHAPTERS = {
    "Genesis": 50, "Psalms": 150, "Mark": 16, "John": 21,
    "Malachi": 4, "Matthew": 28, "Revelation": 22,
}
REAL_VERSES = {
    ("Psalms", 119): 176, ("Mark", 16): 20, ("John", 3): 36,
    ("Malachi", 4): 6, ("Matthew", 1): 25, ("Revelation", 22): 21,
    ("Genesis", 1): 31,
}


def build_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE bible (b INTEGER, c INTEGER, v INTEGER, t TEXT)")
    rows = []
    for index, (canonical_number, name, _) in enumerate(BOOKS, start=1):
        chapters = 1 if canonical_number in SINGLE_CHAPTER_BOOKS else REAL_CHAPTERS.get(name, 3)
        for chapter in range(1, chapters + 1):
            verses = REAL_VERSES.get((name, chapter), 10)
            for verse in range(1, verses + 1):
                # Mark 16 in some manuscripts/exports is missing verse 9 —
                # a real-world gap the navigator must step over.
                if name == "Mark" and chapter == 16 and verse == 9:
                    continue
                rows.append((index, chapter, verse, f"{name} {chapter}:{verse} text."))
    conn.executemany("INSERT INTO bible VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()
    print(f"fixture: {len(rows)} verses across {len(BOOKS)} books")


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="mv_nav_"))
    db_path = tmp / "test_bible.sqlite"
    build_db(db_path)
    bible_schema.CACHE_PATH = tmp / "schema_cache.json"
    bible_db_module.RANGE_CACHE_PATH = tmp / "range_cache.json"

    from verse_navigation import VerseNavigator, VerseRef, parse_reference

    db = bible_db_module.BibleDB(str(db_path), translation="TEST")
    nav = VerseNavigator(db)

    # ── resolve_ref accepts names, abbreviations and numbers ──
    ref = nav.resolve_ref("John", 3, 16)
    assert ref == VerseRef(430, "John", 3, 16), ref
    assert nav.resolve_ref("jn", 3, 16) == ref, "abbreviation should resolve"
    assert nav.resolve_ref(430, 3, 16) == ref, "book number should resolve"
    assert nav.resolve_ref("John", 99, 1) is None, "out-of-range chapter must fail"
    assert nav.resolve_ref("John", 3, 999) is None, "out-of-range verse must fail"
    assert nav.resolve_ref("Nowhere", 1, 1) is None
    print("OK: resolve_ref")

    # ── simple stepping ──
    assert nav.next_verse(ref).verse == 17
    assert nav.prev_verse(ref).verse == 15
    print("OK: next/prev inside a chapter")

    # ── chapter boundary ──
    end_of_ch3 = nav.resolve_ref("John", 3, 36)
    nxt = nav.next_verse(end_of_ch3)
    assert (nxt.book, nxt.chapter, nxt.verse) == ("John", 4, 1), nxt
    back = nav.prev_verse(nxt)
    assert (back.book, back.chapter, back.verse) == ("John", 3, 36), back
    print("OK: chapter boundary")

    # ── book boundary: Malachi 4:6 -> Matthew 1:1 and back ──
    mal = nav.resolve_ref("Malachi", 4, 6)
    mat = nav.next_verse(mal)
    assert (mat.book, mat.chapter, mat.verse) == ("Matthew", 1, 1), mat
    assert nav.prev_verse(mat) == mal
    print("OK: book boundary")

    # ── single-chapter book: Jude 1:x steps out to Revelation 1:1 ──
    jude_last_verse = nav.list_verses(650, 1)[-1]
    jude = nav.resolve_ref("Jude", 1, jude_last_verse)
    after_jude = nav.next_verse(jude)
    assert (after_jude.book, after_jude.chapter) == ("Revelation", 1), after_jude
    assert nav.prev_verse(nav.resolve_ref("Jude", 1, 1)).book == "3 John"
    print("OK: single-chapter book")

    # ── end of Bible stops by default, wraps only when asked ──
    last = nav.resolve_ref("Revelation", 22, 21)
    assert nav.next_verse(last) is None, "must stop at Revelation 22:21"
    first = nav.resolve_ref("Genesis", 1, 1)
    assert nav.prev_verse(first) is None, "must stop at Genesis 1:1"
    wrapping = VerseNavigator(db, wrap_books=True)
    assert wrapping.next_verse(last) == first
    assert wrapping.prev_verse(first) == last
    print("OK: canon boundaries")

    # ── gaps: Mark 16:8 -> 16:10 (no verse 9 in this file) ──
    mark = nav.resolve_ref("Mark", 16, 8)
    assert nav.next_verse(mark).verse == 10, nav.next_verse(mark)
    assert nav.resolve_ref("Mark", 16, 9) is None
    print("OK: missing verse gap")

    # ── long chapter ──
    assert len(nav.list_verses(190, 119)) == 176
    assert db.get_chapter_verse_count(190, 119) == 176
    assert db.get_max_chapter(190) == 150
    psalm_end = nav.resolve_ref("Psalms", 119, 176)
    assert nav.next_verse(psalm_end).chapter == 120
    print("OK: Psalm 119")

    # ── structure listings ──
    books = nav.list_books("all")
    assert len(books) == 66, len(books)
    assert books[0]["book"] == "Genesis" and books[-1]["book"] == "Revelation"
    assert len(nav.list_books("ot")) == 39
    assert len(nav.list_books("nt")) == 27
    assert nav.list_chapters(410) == list(range(1, 17)), "Mark has 16 chapters"
    verses = nav.chapter_verses(410, 16)
    assert len(verses) == 19 and verses[0]["text"].startswith("Mark 16:1")
    print("OK: structure listings")

    # ── verse payload shape matches a detection event ──
    event = nav.verse_event(ref, source="manual")
    assert event["book"] == "John" and event["chapter"] == 3 and event["verse"] == 16
    assert event["text"] and event["source"] == "manual" and event["book_number"] == 430
    print("OK: verse_event payload")

    # ── nearest_ref snaps rather than failing ──
    snapped = nav.nearest_ref("John", 3, 999)
    assert (snapped.chapter, snapped.verse) == (3, 36), snapped
    print("OK: nearest_ref")

    # ── typed references answer themselves; phrases fall through ──
    assert parse_reference("John 3:16") == (430, 3, 16)
    assert parse_reference("1 cor 13:4") == (460, 13, 4)
    assert parse_reference("mat 5 3") == (400, 5, 3)
    assert parse_reference("psalm 119") == (190, 119, None)
    assert parse_reference("Jude 4") == (650, 1, 4), "single-chapter book"
    for phrase in ("love your enemies", "faith hope and love", "john", ""):
        assert parse_reference(phrase) is None, phrase
    print("OK: parse_reference")

    print("\nAll verse navigation checks passed.")


if __name__ == "__main__":
    main()
