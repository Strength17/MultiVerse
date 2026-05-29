# Project Report: MultiVerse Real-Time Scripture Detection

## 1. Project Identity & Overview
MultiVerse is an offline, real-time backend system designed to detect Bible verse references from live audio streams or WAV files.

- **Objective:** Capture audio, transcribe it, detect explicit scripture references or paraphrases, look up the verse in a local SQLite database, and output JSON payloads.
- **Constraints:** Optimized for low-power hardware (Intel Pentium N3530, no AVX). Rigid version pinning for `ctranslate2==3.9.0` and `faster-whisper==1.0.3`.
- **Operating Mode:** Standalone CLI backend. No UI. JSON output to stdout.

## 2. Technical Stack
- **Transcription:** Whisper (local, offline) via `faster-whisper` (fallback to `openai-whisper` if hardware limitations require).
- **Detection (Explicit):** Regex-based engine combined with `rapidfuzz` for fuzzy book name matching.
- **Detection (Paraphrase):** Vector-based semantic search using FAISS and `sentence-transformers` (`all-MiniLM-L6-v2`).
- **Database:** Local SQLite (`data/nkjv.sqlite3`) containing NKJV translation.
- **Audio Pipeline:** `pyaudio` capturing at 16kHz mono. Sliding window buffer (configurable `chunk_seconds`, `overlap_seconds`).

## 3. Data Schema (NKJV SQLite)
- **Table `verses`**: `book_number` (multiples of 10), `chapter`, `verse`, `text` (contains markup `<pb/>`, `<f>`).
- **Table `books`**: Mapping for 66 canonical books.

## 4. The Known Bug & Required Fix
The system currently implements a sliding window buffer (`transcript_buffer = deque(maxlen=2)`), aiming to concatenate the previous (`n-1`) and current (`n`) chunks of text. 

**The Bug:** The functionality to effectively use the combined text (`n-1` + `n`) for verse lookups is not functioning as intended during live tests. 
- **Requirement:** A book/chapter might be mentioned in the `n-1` chunk, and the verse number in the `n` chunk. The detection logic must consistently analyze the concatenation to bridge these references.
- **Goal:** Fix this bridge functionality to ensure accurate detection across chunk boundaries, then commit as `v2.4.0`.

---

## Commit History

| Commit Hash | Message |
| :--- | :--- |
| dbbe8fc | fix: cross-chunk punctuation normalization and remove 'was' alias |
| 41590ad | fix(context): v2.4.0 - implement persistent cross-chunk context tracker |

*Tag created: v2.4.0*
