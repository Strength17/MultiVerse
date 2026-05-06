# tests/test_performance.py
import pytest
import time
from core.bible_db import BibleDB

def test_perf_fts_search(db_conn):
    start = time.perf_counter()
    for _ in range(10):
        db_conn.search_fts("love")
    end = time.perf_counter()
    avg_time = (end - start) / 10
    assert avg_time < 0.1 # Assert < 100ms per search

def test_perf_like_search(db_conn):
    start = time.perf_counter()
    for _ in range(10):
        db_conn.search_like("God")
    end = time.perf_counter()
    avg_time = (end - start) / 10
    assert avg_time < 0.1 # Assert < 100ms per search
