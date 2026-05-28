# MultiVerse Repository Manifest (AI-Optimized Context)
**Objective:** To provide a perfect-fidelity technical and contextual memory of the MultiVerse project for any future AI agent or developer.
**Commit Version:** v2.2.0-stable (Final Backend Baseline)
**Hardware Target:** Intel Pentium N3530 (Atom-class, No AVX, No GPU)

---

## 1. PROJECT INTENT & PHILOSOPHY ("The Soul of MultiVerse")
MultiVerse is a real-time scripture detection system built for high-stakes live environments. 
*   **The Mission:** To listen to a speaker and identify Bible verses (NKJV) with zero internet dependency.
*   **The Constraint:** It must run on 2013-era low-power hardware. Every line of code is written with "Performance per Watt" in mind.
*   **The Strategy:** Use a tiered detection model—Regex for 100% certainty, Vector Search for semantic "near-misses."

---

## 2. HARDWARE & SOFTWARE CONSTRAINTS (CRITICAL)
**DO NOT DEVIATE from these settings without full hardware re-validation:**
*   **CPU:** Intel Pentium N3530. **NO AVX support.**
*   **Version Pin:** `ctranslate2==3.9.0` is the LAST version that runs on this CPU. Newer versions use AVX and will crash.
*   **PyTorch:** Must be the CPU-only build (`--index-url https://download.pytorch.org/whl/cpu`).
*   **Whisper Model:** Optimized for `tiny.en` with `int8` quantization to keep transcription under 5s latency.

---

## 3. ARCHITECTURE OVERVIEW
The system follows a linear pipeline with a rolling buffer:
1.  **Capture (`main.py`):** 16kHz mono audio via PyAudio into a `queue.Queue`.
2.  **Buffer (`main.py`):** 3-second rolling window with 1.5-second overlap.
3.  **Transcribe (`transcriber.py`):** Whisper (`faster-whisper` or `openai-whisper` fallback).
4.  **Detect Tier 1 (`verse_detector.py`):** Regex engine with `rapidfuzz` book matching. 
5.  **Detect Tier 2 (`vector_search.py`):** FAISS index search (Inner Product) using `all-MiniLM-L6-v2`.
6.  **Enrich (`bible_db.py`):** SQLite lookup in `data/nkjv.sqlite3` with tag stripping.
7.  **Output:** Stdout JSON stream.

---

## 4. FILE-BY-FILE BREAKDOWN

### `GEMINI.md` (The Autonomous Constitution)
*   Contains the core operating rules for the AI agent (Rule A-01 to A-11).
*   Defines the 6-Phase build plan and verification gates.
*   **Importance:** This file is the "Master Instruction" that keeps the agent from deviating or asking unnecessary questions.

### `config.ini` (The Brain Stem)
*   Centralized configuration. No hardcoded values in Python files.
*   Key sections: `[audio]`, `[transcription]`, `[detection]`, `[vectors]`.

### `transcriber.py` (The Ears)
*   Implements a mandatory import guard for `faster-whisper`.
*   Uses `tiny.en` and `int8` to prevent CPU stalling.
*   Biased with an `initial_prompt` from config to improve Bible terminology accuracy.

### `verse_detector.py` (The Logic)
*   Uses `word2number` to normalize spoken numbers (e.g., "three" -> "3").
*   Implements "Book-First" validation to prevent false positives like "Song of Solomon" being triggered by common words.
*   Confidence-gated matching.

### `vector_search.py` (The Intuition)
*   Handles semantic paraphrases (e.g., "God so loved the world").
*   L2-normalizes vectors for Cosine Similarity matching in FAISS.
*   Threshold set to `0.72` to balance accuracy vs. noise.

### `bible_db.py` (The Memory)
*   Connects to `data/nkjv.sqlite3`.
*   Implements `clean_verse_text()` using regex to strip `<pb/>`, `<i>`, and `<f>` tags.
*   Maps canonical book names to the database's unique multiples-of-10 IDs (e.g., John = 430).

### `main.py` (The Heartbeat)
*   Orchestrates the threads: One for audio capture, one for processing.
*   Implements the "Sliding Window" logic to ensure verses aren't missed if they cross chunk boundaries.
*   Deduplication logic: Prevents same verse from triggering multiple times within 8 seconds.

---

## 5. RECENT HISTORY & OPTIMIZATIONS
*   **v2.1.0:** Solved the "Zero Memory" bottleneck by implementing INT8 quantization and serializing audio chunks to prevent thread contention.
*   **v2.2.0:** Rewrote the Regex engine to include "Book Context" gating, which eliminated false positives during general conversation.
*   **Current State:** The backend is verified stable and ready for a Frontend/vMix integration.

---

## 6. FUTURE INTEGRATION PATH
*   **Frontend:** Best implemented via a Web Overlay (Browser Source).
*   **Bridge:** Requires a `FastAPI` + `WebSockets` layer added to `main.py` to broadcast JSON detections to the web frontend.
*   **vMix:** Add as a Web Browser input for perfect transparency and alpha-channel animations.

---
**REPORT END**
This manifest is the single source of truth for the MultiVerse Project. 
Created on: May 28, 2026.
