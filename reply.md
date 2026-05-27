# Test Run Details

## Test Run 1
- **Start:** `INFO:__main__:Transcription thread started.` ... `INFO:__main__:Processing test file: tests/test_audio.wav`
- **End:** `{"session_end": true, "verses_triggered": 6, "runtime_seconds": 220}` ... `INFO:__main__:Transcription thread finished.`
- **Triggers:** 6 verses
- **Accuracy/Latency Notes:** 
  - John 6:69 (vector) | Latency 4.32s
  - 1 Corinthians 2:5 (vector) | Latency 4.51s
  - John 4:24 (vector) | Latency 4.41s
  - Ephesians 5:9 (vector) | Latency 18.50s
  - Genesis 1:1 (regex) | Latency 4.37s
  - Genesis 1:27 (vector) | Latency 4.21s

## Test Run 2
- **Start:** `INFO:__main__:Transcription thread started.` ... `INFO:__main__:Processing test file: tests/test_audio.wav`
- **End:** `{"session_end": true, "verses_triggered": 6, "runtime_seconds": 248}` ... `INFO:__main__:Transcription thread finished.`
- **Triggers:** 6 verses
- **Accuracy/Latency Notes:**
  - John 6:69 (vector) | Latency 4.31s
  - 1 Corinthians 2:5 (vector) | Latency 4.60s
  - John 4:24 (vector) | Latency 4.32s
  - Ephesians 5:9 (vector) | Latency 51.24s
  - Genesis 1:1 (regex) | Latency 4.47s
  - Genesis 1:27 (vector) | Latency 4.14s
