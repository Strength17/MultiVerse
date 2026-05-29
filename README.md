# MultiVerse: Real-Time Scripture Detection Backend

MultiVerse is a real-time, offline scripture detection backend that captures audio and identifies Bible verse references using both regex (explicit) and vector-based (paraphrase) matching.

## Features
- **Offline Transcription:** Utilizes Whisper (via `openai-whisper` or `faster-whisper`) for local audio-to-text.
- **Explicit Detection:** Regex engine for standard citations (e.g., "John 3:16").
- **Semantic Detection:** Vector search (FAISS + SentenceTransformers) for paraphrased scripture.
- **Sliding Window Pipeline:** Optimized audio buffering for real-time performance.
- **Hardware-Aware:** Configured to run on resource-constrained hardware (e.g., Intel Bay Trail).

## Setup
1. **Prerequisites:** Ensure Python 3.11+ is installed.
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Database:** Ensure `data/NKJV.SQLite3` is present.
4. **Configuration:** Adjust `config.ini` as needed for thresholds and model settings.

## Running the System
- **Live Mic:**
  ```bash
  python main.py
  ```
- **Test File:**
  ```bash
  python main.py --test-file tests/test_audio.wav
  ```

## Project Structure
- `main.py`: Entry point and pipeline orchestrator.
- `transcriber.py`: Audio transcription logic.
- `verse_detector.py`: Regex-based verse matching.
- `vector_search.py`: Vector-based semantic matching.
- `bible_db.py`: SQLite interface for verse lookups.
- `build_vector_db.py`: One-time script to index the Bible.
- `config.ini`: System settings.
