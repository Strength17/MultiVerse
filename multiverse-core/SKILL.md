---
name: multiverse-core
description: Core engine logic for MultiVerse. Use for audio capture, transcription, verse detection, and vMix bridge operations.
---

# Multiverse Core Engine Skill

## Workflow

### 1. Audio and Transcription (T-10–T-15)
- **Audio Capture**: Use `sounddevice` with callback pattern (ref: Lesson L-004). Never use blocking `InputStream.read()`.
- **Transcription**: Wrap `faster-whisper`. Handle model downloads (ref: Lesson L-006).
- **Bible Injection**: Use book names from `data/book_names.py` for Whisper initial prompt (ref: Lesson L-002: keep prompt < 200 tokens).

### 2. Verse Detection (T-16–T-22)
- **Engine**: Combine `regex` for pattern matching with `rapidfuzz` for book names.
- **Normalisation**: Use `utils/number_words.py` for spoken numbers.
- **Scoring**: Implement confidence thresholding.

### 3. Database (T-23–T-27)
- **Interface**: SQLite (`sqlite3` stdlib).
- **Threading**: Create new connections per thread (ref: Lesson L-005).

### 4. vMix Bridge (T-28–T-33)
- **API**: HTTP requests to `localhost:8088`.
- **Error Handling**: Use `timeout=2` to prevent UI freezing (ref: Lesson L-003).

## Standards
- Always read `config.ini` for settings.
- Use `logger` for all operations.
- PyQt6 threads for all long-running tasks.
