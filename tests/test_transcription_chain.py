# tests/test_transcription_chain.py
import numpy as np
import logging
from core.audio_capture import AudioCapture
from core.transcriber import Transcriber
from core.audio_processor import AudioProcessor
from core.vocabulary_injection import get_initial_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_transcription_chain():
    logger.info("Initializing transcription test...")
    
    # 1. Initialize Transcriber
    from configparser import ConfigParser
    config = ConfigParser()
    config.add_section('transcription')
    config.add_section('audio')
    config.set('transcription', 'model_size', 'base.en')
    config.set('transcription', 'device', 'cpu')
    config.set('audio', 'chunk_seconds', '5')
    transcriber = Transcriber(config)
    transcriber.initialize_model()
    
    # 2. Mock Audio Capture (Simulating 5 seconds of audio)
    sample_rate = 16000
    dummy_audio = np.zeros(5 * sample_rate, dtype=np.float32)
    
    # 3. Transcribe
    prompt = get_initial_prompt()
    logger.info(f"Transcribing... (prompt length: {len(prompt)})")
    
    # Note: Dummy audio will likely result in silence, but this tests the execution path
    result = transcriber.transcribe(dummy_audio, initial_prompt=prompt)
    logger.info(f"Transcription result: '{result}'")
    
    logger.info("Transcription test finished.")

if __name__ == "__main__":
    test_transcription_chain()
