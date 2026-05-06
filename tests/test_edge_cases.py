# tests/test_edge_cases.py
import pytest
from core.bible_db import BibleDB

def test_edge_case_nonexistent_verse(db_conn):
    # Book=99 is out of range
    text = db_conn.lookup_verse(99, 1, 1)
    assert text is None

def test_edge_case_empty_search(db_conn):
    results = db_conn.search_fts("")
    assert results == []

def test_edge_case_gibberish_search(db_conn):
    results = db_conn.search_fts("asdfghjklqwerty")
    assert results == []

def test_edge_case_normalization(db_conn):
    # Genesis 1:1
    text = db_conn.lookup_verse(1, 1, 1)
    assert text is not None
    assert "In the beginning" in text
