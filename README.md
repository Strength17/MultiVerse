# MultiVerse Backend

Real-time scripture detection backend.

## JSON Output Format

The backend streams JSON Lines (`JSONL`) to stdout.

**Detection Event:**
```json
{"triggered": true, "source": "regex", "book": "John", "chapter": 3, "verse": 16, "text": "For God so loved the world...", "latency_ms": 150}
```

**Heartbeat/No Detection:**
```json
{"triggered": false}
```

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python main.py`
