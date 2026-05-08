# tests/test_bible_db.py
import pytest
from core.bible_db import BibleDB

@pytest.fixture
def db():
    return BibleDB()

def test_lookup_genesis_1_1(db):
    """Verify Genesis 1:1 lookup."""
    # Genesis is Book 1
    verse_text = db.lookup_verse(1, 1, 1)
    assert verse_text is not None
    assert "In the beginning" in verse_text

def test_lookup_john_3_16(db):
    """Verify John 3:16 lookup."""
    # John is Book 43
    verse_text = db.lookup_verse(43, 3, 16)
    assert verse_text is not None
    assert "For God so loved the world" in verse_text

def test_lookup_invalid_verse(db):
    """Verify lookup returns None for non-existent verse."""
    # Genesis 1:999 doesn't exist
    verse_text = db.lookup_verse(1, 1, 999)
    assert verse_text is None

def test_search_verse_keyword(db):
    """Verify keyword search returns results."""
    results = db.search_fts("beginning")
    assert len(results) > 0
    # First result should be Genesis 1:1 (Book 1)
    found_gen_1_1 = False
    for r in results:
        if r["reference"] == "Genesis 1:1":
            found_gen_1_1 = True
            break
    assert found_gen_1_1

def test_search_no_results(db):
    """Verify search returns empty list for non-existent keyword."""
    results = db.search_fts("nonexistentkeyword12345")
    assert results == []
