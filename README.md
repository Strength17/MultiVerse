# MultiVerse — Real-Time Scripture Detection & Display System

MultiVerse is a real-time scripture detection and display system for live worship services. It transcribes sermon audio, detects Bible verse references, and automatically displays them on a secondary screen or projector.

## Features
- Real-time audio transcription using Whisper (medium.en).
- Bible verse reference detection (regex + fuzzy matching).
- Standalone PyQt6 fullscreen scripture display window.
- Offline-first operation (all models and data local).
- Operator UI for reviewing and sending verses.

## Setup
1. Clone the repository.
2. Install requirements: `pip install -r requirements.txt`.
3. Configure `config.ini` with local settings.
4. Run `python main.py`.

## License
Proprietary.
