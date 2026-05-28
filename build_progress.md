# Build Progress - v2.3.0-bugfix

## Summary of Fixes
1.  **VAD Gate Moved:** Silence is now discarded at the capture stage in `main.py`. This prevents Whisper from processing empty audio, eliminating 30-60s latency spikes.
2.  **Book Priority:** Current window transcript now takes precedence over book memory in `verse_detector.py`. This eliminates "double-fire" errors where a previous book context incorrectly triggered a new chapter/verse citation.
3.  **Hyphen Support:** Hyphens are now accepted as chapter-verse separators (e.g., "Revelation 1-1") in the regex engine.
4.  **False Positive Elimination:** Refined `_find_book` logic to explicitly reject single-digit strings and purely numeric candidates as book names, fixing the "1" -> "1 Chronicles" false trigger.

## Verification Results (3 Consecutive Runs)
*   **Unit Tests (Groups A, B, C, D):** 100% PASS
*   **Pipeline Tests (Group E):**
    *   Romans 8:1: ~3.9s
    *   John 4:24: ~4.1s
    *   Genesis 1:1: ~4.5s
    *   Genesis 1:27: ~4.2s
*   **Silence Spikes:** 0 (All silence chunks skipped < 0.3s)
*   **False Fires:** 0 (Ruth 4:4 and Song of Solomon eliminated)
*   **HTTP Calls:** 0 (Offline mode confirmed)

## Tagging
*   **Version:** v2.3.0-bugfix
*   **Status:** Stable

**Build complete.**
