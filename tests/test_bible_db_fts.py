# tests/test_bible_db_fts.py
from core.bible_db import BibleDB

def test_fts_search_results(db_conn):
    results = db_conn.search_fts("God loved the world")
    assert isinstance(results, list)
    if results:
        assert "reference" in results[0]
        assert "verse" in results[0]

def test_like_search_fallback(db_conn):
    results = db_conn.search_like("love")
    assert len(results) > 0
