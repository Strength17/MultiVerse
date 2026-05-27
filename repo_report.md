# repo_report.md

## 1. File Summary
- `main.py`: Pipeline orchestrator and audio queue manager.
- `transcriber.py`: Whisper inference wrapper using greedy decoding.
- `verse_detector.py`: Regex-based scripture detector with book-name memory.
- `vector_search.py`: FAISS-based semantic similarity search engine.
- `bible_db.py`: SQLite NKJV interface and markup stripper.
- `build_vector_db.py`: One-time script for semantic FAISS indexing.
- `config.ini`: Centralized runtime configurations.
- `requirements.txt`: Project dependency manifest.
- `logs/`: Runtime logs and performance timing.
- `tests/`: Ground-truth verification audio.
- `golden_run/`: Benchmark reference snapshot.

## 2. Config.ini (Active)
- `[audio]`: sample_rate=16000, chunk_seconds=4, overlap_seconds=2.5, max_queue_size=1
- `[transcription]`: model_size=tiny.en, compute_type=int8
- `[detection]`: vector_threshold=0.72, regex_threshold=0.75, cooldown_seconds=8

## 3. Dependency Versions (Key)
- `openai-whisper`: 20250625
- `pywhispercpp`: 1.4.1
- `torch`: 2.6.0+cpu
- `sentence-transformers`: 5.4.1
- `faiss-cpu`: 1.14.2

## 4. Data Flow
Microphone -> PyAudio -> Sliding Window (Queue) -> Transcriber (Whisper) -> Verse Detector (Regex + Memory) -> Vector Search -> Bible DB -> JSON Output.

## 5. Sliding Window Specs
- Chunk: 4s
- Overlap: 2.5s
- Step: 1.5s
- Max Queue Size: 1

## 6. Transcription Engine
- Backend: `openai-whisper` (tiny.en).
- Parameters: `beam_size=1`, `temperature=0`, `condition_on_previous_text=False`, `fp16=False`.

## 7. Vector Search
- Threshold: 0.72
- Model: `all-MiniLM-L6-v2`

## 8. Best Benchmark (Phase 12)
- Recorded: 11 triggers, 105s total runtime (Golden Run).
- Latest: 7 triggers, 268s runtime (Regressed).
- Latency per trigger: ~4.5s.

## 9. Known Issues
- CPU Saturation: Pentium N3530 cannot maintain real-time transcription throughput, leading to queue overflow and dropped audio segments.
- Semantic Regression: Paraphrase detection is sensitive to transcript filler words added by the tiny.en model.
