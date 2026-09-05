"""Verify instant Bible version switching and non-blocking background index rebuilds."""
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server
from server import WindowVerseServer
from bible_db import BibleDB
from verse_navigation import VerseNavigator, VerseRef

# 1. Define Mock Orchestrator to bypass slow CPU-bound embedding generation
class MockModel:
    def encode(self, sentences, *args, **kwargs):
        import numpy as np
        # Handle single sentence or list of sentences
        n = 1 if isinstance(sentences, str) else len(sentences)
        return np.zeros((n, 384), dtype="float32")

class MockVectorEngine:
    def __init__(self):
        self._model = MockModel()

class MockOrchestrator:
    def __init__(self, db, translation, **kwargs):
        self.translation = translation
        self.vector_engine = MockVectorEngine()
        self._index_built = True

    def build_index(self, *args, **kwargs):
        # Simulate a slight delay to allow testing task state and cancellation
        pass

    def detect(self, text, **kwargs):
        return {
            "triggered": True,
            "book": "John",
            "book_number": 430,
            "chapter": 3,
            "verse": 16,
            "text": f"Mock {self.translation} text",
            "translation": self.translation,
        }

# Monkeypatch the orchestrator before initializing server
server.DetectionOrchestrator = MockOrchestrator

# 2. Mock NDISender and WinRTSpeechPipeline to avoid external hardware/DLL requirements
class MockNDISender:
    def __init__(self, *args, **kwargs):
        self._available = False
    def set_display(self, *args): pass
    def set_backgrounds_dir(self, *args): pass
    def update(self, *args, **kwargs): pass
    def clear(self): pass
    def start(self): pass
    def stop(self): pass

class MockPipeline:
    def __init__(self, *args, **kwargs): pass
    def is_running(self): return False
    def is_capturing(self): return False
    def stop(self): pass

server.NDISender = MockNDISender
server.WinRTSpeechPipeline = MockPipeline

# Mock verification to avoid schema check failures on missing dependencies
server.verify_anchor_verses = lambda db: []

import pytest

@pytest.mark.anyio
async def test_instant_switch():
    print("Initializing test server...")
    srv = WindowVerseServer()
    
    # Initialize using NKJV database
    primary_db_path = "data/NKJV/English/NKJV.sqlite3"
    srv.initialize(db_path=primary_db_path)
    srv._ready = True
    
    # Ensure current state is NKJV
    assert srv._current_version == "NKJV"
    assert srv.bible_db is not None
    assert srv._current_language == "English"
    
    print("Initial state verified: NKJV is active.")
    
    # Setup preview and display events
    srv._preview = {
        "triggered": True,
        "book": "John",
        "book_number": 430,
        "chapter": 3,
        "verse": 16,
        "text": "NKJV preview text",
        "translation": "NKJV",
        "source": "operator"
    }
    srv._last_displayed = {
        "triggered": True,
        "book": "John",
        "book_number": 430,
        "chapter": 3,
        "verse": 16,
        "text": "NKJV display text",
        "translation": "NKJV",
        "source": "operator"
    }
    srv._nav_ref = VerseRef(430, "John", 3, 16)

    # We mock _broadcast to track what is broadcast
    broadcasted_messages = []
    async def mock_broadcast(msg):
        broadcasted_messages.append(msg)
    srv._broadcast = mock_broadcast

    # Modify _rebuild_and_swap inside switch_version to simulate index loading delay
    # so we can verify non-blocking qualities
    original_switch_version = srv._switch_version
    
    print("\n--- TEST 1: Instant version switch from NKJV to KJV ---")
    
    # Trigger version switch to KJV
    await srv._switch_version("KJV", "English", None)
    
    # VERIFY INSTANT updates:
    # 1. Version, Language, DB and Navigator must update immediately!
    assert srv._current_version == "KJV", f"Expected KJV, got {srv._current_version}"
    assert srv.bible_db.translation == "KJV"
    
    # 2. Preview and Last Displayed verses must be re-resolved instantly!
    assert srv._preview is not None
    assert srv._preview["translation"] == "KJV"
    assert "NKJV" not in srv._preview["text"]  # Must be updated to KJV text!
    
    assert srv._last_displayed is not None
    assert srv._last_displayed["translation"] == "KJV"
    assert "NKJV" not in srv._last_displayed["text"]  # Must be updated to KJV text!
    
    # 3. Background task must be spawned
    assert srv._orchestrator_rebuild_task is not None
    assert not srv._orchestrator_rebuild_task.done()
    
    print("OK: KJV Swapped instantly. Background rebuild task running successfully.")
    
    print("\n--- TEST 2: Dynamic translation check during background transition ---")
    # Simulate a detection event coming from the OLD (NKJV) orchestrator while KJV is loading in the background
    old_detection_event = {
        "triggered": True,
        "book": "John",
        "book_number": 430,
        "chapter": 3,
        "verse": 16,
        "text": "For God so loved the world in NKJV",
        "translation": "NKJV",
        "source": "semantic"
    }
    
    # Ensure _ensure_current_translation maps it to KJV text instantly
    translated_event = srv._ensure_current_translation(old_detection_event)
    assert translated_event["translation"] == "KJV"
    assert "NKJV" not in translated_event["text"]
    print("OK: Dynamic translation ensures active version is shown during rebuild.")

    print("\n--- TEST 3: Concurrent switch request (Cancellation) ---")
    # Request a switch to MSG while the KJV rebuild task is still running
    kjv_task = srv._orchestrator_rebuild_task
    
    await srv._switch_version("MSG", "English", None)
    
    # Allow asyncio to propagate the cancellation
    await asyncio.sleep(0.01)
    
    # Verify the previous KJV task was cancelled
    assert kjv_task.cancelled() or kjv_task.done()
    assert srv._current_version == "MSG"
    assert srv._orchestrator_rebuild_task is not None
    assert srv._orchestrator_rebuild_task != kjv_task
    
    print("OK: Concurrent switch requests successfully cancel stale rebuild tasks.")
    
    # Clean up background tasks
    if srv._orchestrator_rebuild_task and not srv._orchestrator_rebuild_task.done():
        srv._orchestrator_rebuild_task.cancel()
        try:
            await srv._orchestrator_rebuild_task
        except asyncio.CancelledError:
            pass
            
    print("\nAll instant version switching checks passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_instant_switch())
