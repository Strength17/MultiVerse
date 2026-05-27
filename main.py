# main.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import time
import queue
import threading
import logging
import configparser
import numpy as np
import json
import argparse
import signal
from collections import deque

from verse_detector import detect_explicit
from bible_db import get_verse
from vector_search import search_paraphrase
from transcriber import transcribe_chunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/multiverse.log"),
        logging.StreamHandler(sys.stderr) # Log to stderr, stdout is for JSON
    ]
)
logger = logging.getLogger(__name__)

# Load config
config = configparser.ConfigParser()
config.read('config.ini')

SAMPLE_RATE = config.getint('audio', 'sample_rate', fallback=16000)
CHUNK_SECONDS = config.getfloat('audio', 'chunk_seconds', fallback=3.0)
OVERLAP_SECONDS = config.getfloat('audio', 'overlap_seconds', fallback=1.5)
CHANNELS = config.getint('audio', 'channels', fallback=1)
INPUT_DEVICE_INDEX = config.getint('audio', 'input_device_index', fallback=0)
COOLDOWN_SECONDS = config.getfloat('detection', 'cooldown_seconds', fallback=8.0)
MAX_QUEUE_SIZE = config.getint('audio', 'max_queue_size', fallback=2)

# Derived values
CHUNK_SAMPLES = int(CHUNK_SECONDS * SAMPLE_RATE)
STEP_SAMPLES = int((CHUNK_SECONDS - OVERLAP_SECONDS) * SAMPLE_RATE)

# Global state
audio_queue = queue.Queue()
is_running = True

def signal_handler(sig, frame):
    global is_running
    logger.info("Shutdown signal received.")
    is_running = False

signal.signal(signal.SIGINT, signal_handler)

def _enqueue_window(audio_queue: queue.Queue, window: np.ndarray, max_size: int) -> None:
    """
    Add a window to the processing queue.
    """
    try:
        audio_queue.put_nowait(window.copy())
    except queue.Full:
        logger.warning("Queue full — skipping new window, processing backlog first")

def process_audio_thread():
    """
    Main processing loop. Reads audio chunks from the queue, transcribes
    each chunk exactly once (no audio reprocessing), appends the transcript
    to a rolling text buffer, and runs detection on the combined buffer text.

    Cross-chunk verse references (e.g. 'Romans' in chunk N, '8:1' in chunk N+1)
    are caught because the combined buffer contains both chunks as a single string.

    Args:
        audio_queue:   queue.Queue of numpy float32 audio chunks.
        config:        ConfigParser object with all settings.
        running_flag:  threading.Event — clear to stop the loop.
    """
    text_buffer_depth = int(config.get('audio', 'text_buffer_depth', fallback='2'))
    transcript_buffer = deque(maxlen=text_buffer_depth)
    cooldown_tracker = {}
    cooldown_seconds = float(config.get('detection', 'cooldown_seconds', fallback='8'))

    logger.info("Transcript buffer initialised: depth=%d (%.0fs context)",
                text_buffer_depth,
                text_buffer_depth * float(config.get('audio', 'chunk_seconds')))

    verses_count = 0
    start_time = time.time()

    while is_running or not audio_queue.empty():
        try:
            chunk = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # ── Step 1: Transcribe new audio ONCE ──────────────────────────────
        t_start = time.time()
        new_text = transcribe_chunk(chunk).strip()
        t_transcribe = time.time() - t_start

        if not new_text:
            logger.debug("Empty transcript — skipping")
            continue

        logger.info("Transcript: '%s'  (%.2fs)", new_text, t_transcribe)

        # ── Step 2: Add to text buffer ──────────────────────────────────────
        transcript_buffer.append(new_text)

        # ── Step 3: Combine buffer for detection ───────────────────────────
        combined_text = ' '.join(transcript_buffer)
        logger.debug("Combined buffer (%d chunks): '%s'", len(transcript_buffer), combined_text)

        # ── Step 4: Detect ─────────────────────────────────────────────────
        result = detect_explicit(combined_text)
        source = 'regex'
        if result is None:
            result = search_paraphrase(combined_text)
            source = 'vector'

        if result is None:
            print('{"triggered": false}', flush=True)
            continue

        # ── Step 5: Cooldown check ─────────────────────────────────────────
        verse_key = (result.get('book', ''), result.get('chapter', 0), result.get('verse', 0))
        now = time.time()
        last_trigger = cooldown_tracker.get(verse_key, 0)
        if now - last_trigger < cooldown_seconds:
            logger.debug("Cooldown active for %s — suppressing", verse_key)
            print('{"triggered": false}', flush=True)
            continue

        # ── Step 6: DB lookup and output ───────────────────────────────────
        verse_data = get_verse(result['book'], result['chapter'], result.get('verse'))
        if verse_data:
            cooldown_tracker[verse_key] = now
            latency = time.time() - t_start
            output = {**verse_data, 'triggered': True, 'source': source,
                      'confidence': result.get('score', 1.0)}
            print(json.dumps(output), flush=True)
            logger.info("TRIGGERED: %s %d:%d via %s (latency %.2fs)",
                        result['book'], result.get('chapter', 0),
                        result.get('verse', 0), source, latency)
            verses_count += 1
        else:
            logger.warning("DB lookup failed for %s", result)
            print('{"triggered": false}', flush=True)

    runtime = time.time() - start_time
    print(json.dumps({"session_end": True, "verses_triggered": verses_count, "runtime_seconds": int(runtime)}), flush=True)
    logger.info("Transcription thread finished.")

def run_live():
    """
    Captures audio from the microphone.
    """
    import pyaudio
    
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=1024,
            input_device_index=None # Use default
        )
    except Exception as e:
        logger.error(f"Could not open audio stream: {e}")
        return

    logger.info("Live mic started. Speak now...")
    
    audio_buffer = np.array([], dtype=np.float32)
    
    while is_running:
        try:
            data = stream.read(1024, exception_on_overflow=False)
            new_samples = np.frombuffer(data, dtype=np.float32)
            audio_buffer = np.concatenate([audio_buffer, new_samples])
            
            if len(audio_buffer) >= CHUNK_SAMPLES:
                window = audio_buffer[-CHUNK_SAMPLES:]
                _enqueue_window(audio_queue, window, MAX_QUEUE_SIZE)
                # Advance by step
                audio_buffer = audio_buffer[STEP_SAMPLES:]
        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            break
            
    stream.stop_stream()
    stream.close()
    p.terminate()
    logger.info("Live mic stopped.")

def run_test_file(file_path):
    """
    Processes a WAV file.
    """
    import librosa
    logger.info(f"Processing test file: {file_path}")
    
    try:
        audio, _ = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    except Exception as e:
        logger.error(f"Could not load test file: {e}")
        return

    # Simulate the sliding window on the full audio
    ptr = 0
    while ptr + CHUNK_SAMPLES <= len(audio):
        window = audio[ptr : ptr + CHUNK_SAMPLES]
        audio_queue.put(window.copy())
        ptr += STEP_SAMPLES
        
    logger.info("Test file queued for processing.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MultiVerse Backend")
    parser.add_argument("--test-file", help="Path to a WAV file to process instead of live mic")
    args = parser.parse_args()

    # Model warm-up: process a dummy query to pre-load embedding model weights
    logger.info("Warming up embedding model...")
    search_paraphrase("In the beginning God created the heavens and the earth.")
    logger.info("Model warm-up complete.")

    # Start processing thread
    proc_thread = threading.Thread(target=process_audio_thread)
    proc_thread.start()

    if args.test_file:
        run_test_file(args.test_file)
        # Wait for queue to empty
        while not audio_queue.empty():
            time.sleep(1)
        is_running = False
    else:
        run_live()

    proc_thread.join()
    logger.info("Main process finished.")
