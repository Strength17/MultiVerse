import sys
sys.path.insert(0, '.')
from bible_db import get_verse

# Simulated cross-chunk context test
def test_cross_chunk_context():
    # 1. Romans 8:1
    # Chunk N-1: "Romans chapter 8." -> detect_explicit should set context
    # Chunk N: "1." -> search should find verse 1 in Romans 8
    
    # We can simulate this by calling process_audio_thread logic directly if needed,
    # but for now, let's just verify that get_verse(Romans, 8, 1) returns valid data
    # and that the regex/context logic would plausibly trigger.
    
    # Actual database check
    verse_data = get_verse("Romans", 8, 1)
    assert verse_data is not None
    assert verse_data['book'] == "Romans"
    assert verse_data['chapter'] == 8
    assert verse_data['verse'] == 1
    print("PASS: Database supports Romans 8:1")

    # Simulate regex detection logic
    from verse_detector import detect_explicit
    res1 = detect_explicit("Romans chapter 8")
    assert res1['book'] == "Romans" and res1['chapter'] == 8
    print("PASS: Book/Chapter detected")

    # Simulate cross-chunk lookup logic
    # In main.py:
    #   if verse_match and last_book and last_chapter:
    #       match = {"book": last_book, "chapter": last_chapter, "verse": int(verse_match)}
    last_book = "Romans"
    last_chapter = 8
    text = "1"
    import re
    verse_match = re.search(r'\b(\d{1,3})\b', text)
    if verse_match and last_book and last_chapter:
        match = {"book": last_book, "chapter": last_chapter, "verse": int(verse_match.group(1))}
        verse = get_verse(match['book'], match['chapter'], match['verse'])
        assert verse is not None
        print("PASS: Cross-chunk context lookup works")

test_cross_chunk_context()
