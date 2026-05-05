# tests/test_verse_detector.py
import pytest
import logging
from core.verse_detector import VerseDetector

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def detector():
    return VerseDetector(confidence_threshold=0.70)

def test_detect_simple_reference(detector):
    text = "Please open your Bibles to John 3:16"
    results = detector.detect(text)
    # The current regex requires space after book
    assert len(results) == 1
    assert results[0]['book'] == 'John'
    assert results[0]['chapter'] == 3
    assert results[0]['verse'] == 16

def test_detect_spoken_numbers(detector):
    text = "Read with me from Genesis one twelve"
    results = detector.detect(text)
    assert len(results) == 1
    assert results[0]['book'] == 'Genesis'
    assert results[0]['chapter'] == 1
    # Verse part "twelve" is matched after the chapter
    assert results[0]['verse'] == 12

def test_detect_multiple_references(detector):
    text = "We are reading Romans eight twenty-eight, and also Psalm twenty-three one"
    results = detector.detect(text)
    assert len(results) >= 2

def test_confidence_threshold(detector):
    text = "Open to John 3:16"
    results = detector.detect(text)
    assert len(results) == 1
    assert results[0]['book'] == 'John'
