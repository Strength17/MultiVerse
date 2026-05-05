# tests/test_transcription_accuracy.py

import logging
from core.transcriber import Transcriber
import os

def test_transcription_accuracy():
    # Setup
    transcriber = Transcriber()
    transcriber.initialize_model()
    
    # Paths
    audio_path = "Tic Raw Anthem.m4a"
    lyrics_path = "Tic Raw Anthem - lyrics.txt"
    
    # Load Ground Truth
    with open(lyrics_path, 'r', encoding='utf-8') as f:
        ground_truth = f.read().lower().replace('\n', ' ')
    
    # Transcribe
    # NOTE: Audio must be accessible to Whisper model (faster-whisper handles file path)
    # Using the provided file path directly
    result = transcriber.transcribe(audio_path)
    result_normalized = result.lower().replace('\n', ' ')
    
    print(f"\n--- Accuracy Test ---\nGround Truth: {ground_truth[:100]}...\nResult: {result_normalized[:100]}...")
    
    # Simple check for keyword coverage as an accuracy proxy
    keywords = ["summit", "technovation", "yaounde", "cameroon", "emergence"]
    for kw in keywords:
        assert kw in result_normalized, f"Keyword '{kw}' not found in transcript."

if __name__ == '__main__':
    test_transcription_accuracy()
