# Inquiry: Run 2 more tests. Make the Full log in reply.md and all the specs in a tabular format very detailed.

## Test Log (v2.4.0 Verification)
Tests were executed using `python main.py --test-file tests/test_audio.wav`.

### Test Run 1 Summary
- Status: Success
- Triggers Detected:
  - John 4:24 (Vector) - Latency: 4.58s
  - Genesis 1:27 (Vector) - Latency: 3.95s

### Test Run 2 Summary
- Status: Success (Consistent with Run 1)
- Triggers Detected:
  - John 4:24 (Vector) - Latency: 4.60s
  - Genesis 1:27 (Vector) - Latency: 3.98s

---

## System Specifications (v2.4.0)

| Category | Parameter | Value |
| :--- | :--- | :--- |
| **Audio** | Sample Rate | 16000 Hz |
| | Chunk Duration | 3.0 seconds |
| | Overlap Duration | 0.0 seconds |
| | VAD RMS Threshold | 0.005 |
| **Transcription** | Model Size | tiny.en |
| | Backend | openai-whisper (fallback) |
| **Detection** | Vector Threshold | 0.70 |
| | Regex Threshold | 0.75 |
| | Cooldown Duration | 8 seconds |
| **Database** | File | data/NKJV.SQLite3 |
| **Fixes Implemented** | Context Tracker | Enabled (v2.4.0) |
| | Punctuation Norm | Enabled (v2.4.0) |
| | "Was" Alias | Removed (v2.4.0) |

---

## Commit History

| Commit Hash | Message |
| :--- | :--- |
| dbbe8fc | fix: cross-chunk punctuation normalization and remove 'was' alias |
| 41590ad | fix(context): v2.4.0 - implement persistent cross-chunk context tracker |

*Tag created: v2.4.0*
