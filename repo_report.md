# MultiVerse System Architecture & Development Specification

## 1. Overview
MultiVerse is a high-performance, real-time scripture detection backend designed for low-resource environments (e.g., Intel Bay Trail). It processes live microphone audio or WAV files, performing local transcription via Whisper, followed by dual-method detection (Regex for explicit references and Vector search for paraphrases).

## 2. Core Modules
### A. Regex Detector (`verse_detector.py`)
- **Purpose**: Captures explicit scriptural references.
- **Dependencies**: `re`, `rapidfuzz`, `word2number`, `configparser`.
- **Logic**: Implements a series of patterns to convert spoken numbers into digits and matches against a canon list. Uses `rapidfuzz` to mitigate transcription inaccuracies in book titles.
- **Verification**: Includes 20 unit tests in the `if __name__ == '__main__':` block.

### B. Bible Database (`bible_db.py`)
- **Purpose**: Provides high-speed lookups of KJV scripture text.
- **Architecture**: SQLite3 (`data/nkjv.sqlite3`). 
- **Interface**: `get_verse(book_name, chapter, verse)` returns a dictionary schema: `{"book": str, "chapter": int, "verse": int, "text": str}`.
- **Constraints**: Uses context managers for all DB connections to ensure thread safety and resource cleanup.

### C. Vector Search (`vector_search.py`)
- **Purpose**: Detects semantic paraphrases that don't match regex.
- **Architecture**: FAISS flat index (`data/bible_vectors.index`) and mapping (`data/bible_verse_map.pkl`).
- **Flow**:
  1. Encode query with `all-MiniLM-L6-v2`.
  2. L2-normalize.
  3. Perform inner-product search in FAISS.
  4. Compare against `[detection] vector_threshold`.

### D. Transcription (`transcriber.py`)
- **Purpose**: Converts audio to text.
- **Architecture**:
  - Primary: `faster-whisper` (`ctranslate2==3.9.0`, `faster-whisper==1.0.3`) for high-efficiency CPU inference.
  - Fallback: `openai-whisper` (base.en).
- **Hard Hardware constraint**: No AVX (Intel Pentium N3530). `ctranslate2` must be pinned to 3.9.0.

### E. Pipeline & Main Runner (`main.py`)
- **Architecture**: Multi-threaded.
- **Audio Buffer**: Rolling sliding-window (NumPy array).
  - Window size: 3s.
  - Step size: 1.5s.
- **Concurrency**: `queue.Queue` manages handoff between audio capture thread and transcription/detection thread.
- **Output**: JSON streaming to stdout.

## 3. Data Flow & Pipeline Logic
1. **Input**: Audio is captured via `pyaudio` -> stored in `audio_buffer`.
2. **Buffer Logic**: When the buffer exceeds `step_samples`, the latest `chunk_samples` (3s window) is copied to a queue.
3. **Processing**:
   - Transcribe: `transcribe_chunk`.
   - Explicit Detect: `detect_explicit`.
   - Vector Detect: `search_paraphrase`.
   - Cooldown: Verse (book, ch, v) is suppressed for 8s post-trigger.

## 4. Configuration & Standards
- **Settings**: All thresholds (vector, confidence), timings (overlap, window), and model paths are defined in `config.ini`.
- **Logging**: Uses `logging.getLogger(__name__)`. Rotates logs in `logs/`.
- **Documentation**: All functions require docstrings. File headers must follow `path/to/filename.py` format.

## 5. Troubleshooting & Maintenance
- **Missing DB**: Check `data/nkjv.sqlite3`.
- **Vector Search Failure**: Ensure `build_vector_db.py` was run successfully.
- **Illegal Instruction (Crash)**: Indicates the system is attempting to use AVX instructions. Ensure `ctranslate2` is exactly 3.9.0.
- **Dependencies**: Use `requirements.txt` strictly.
