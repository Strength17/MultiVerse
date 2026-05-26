# main.py

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
triggered_verses = {} # (book, chap, verse) -> last_trigger_time

def signal_handler(sig, frame):
    global is_running
    logger.info("Shutdown signal received.")
    is_running = False

signal.signal(signal.SIGINT, signal_handler)

def _enqueue_window(audio_queue: queue.Queue, window: np.ndarray, max_size: int) -> None:
    """
    Add a window to the processing queue.
    If the queue is full, skip the incoming window and let the existing
    backlog process in order. This ensures early verses (like Romans 8:1)
    are never dropped in favour of newer audio.
    """
    try:
        audio_queue.put_nowait(window.copy())
    except queue.Full:
        logger.warning("Queue full — skipping new window, processing backlog first")

def is_in_cooldown(book, chapter, verse):
    """
    Checks if a verse was recently triggered.
    """
    key = (book, chapter, verse)
    now = time.time()
    if key in triggered_verses:
        if now - triggered_verses[key] < COOLDOWN_SECONDS:
            return True
    return False

def mark_triggered(book, chapter, verse):
    """
    Marks a verse as triggered to start cooldown.
    """
    triggered_verses[(book, chapter, verse)] = time.time()

def process_audio_thread():
    """
    Consumes audio windows from the queue and runs the detection pipeline.
    """
    logger.info("Transcription thread started.")
    verses_count = 0
    start_time = time.time()
    
    while is_running or not audio_queue.empty():
        try:
            window = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # Record timestamp for latency tracking
        window_enqueue_time = time.time()

        # 1. Transcribe
        text = transcribe_chunk(window)
        if not text:
            print(json.dumps({"triggered": False}))
            sys.stdout.flush()
            continue

        logger.info(f"Transcript: '{text}'")
        
        match = None
        source = None
        
        # 2. Regex Detection
        regex_match = detect_explicit(text)
        if regex_match:
            verse_data = get_verse(regex_match['book'], regex_match['chapter'], regex_match['verse'])
            if verse_data:
                if not is_in_cooldown(verse_data['book'], verse_data['chapter'], verse_data['verse']):
                    match = verse_data
                    source = "regex"
        
        # 3. Vector Search (if no regex match)
        if not match:
            vector_match = search_paraphrase(text)
            if vector_match:
                verse_data = get_verse(vector_match['book'], vector_match['chapter'], vector_match['verse'])
                if verse_data:
                    if not is_in_cooldown(verse_data['book'], verse_data['chapter'], verse_data['verse']):
                        match = verse_data
                        source = "vector"
                        match['confidence'] = float(vector_match['score'])

        # 4. Output Result
        if match:
            match['triggered'] = True
            match['source'] = source
            if 'confidence' not in match:
                match['confidence'] = 1.0
                
            latency = time.time() - window_enqueue_time
            print(json.dumps(match))
            sys.stdout.flush()
            mark_triggered(match['book'], match['chapter'], match['verse'])
            verses_count += 1
            logger.info(f"TRIGGERED: {match['book']} {match['chapter']}:{match['verse']} via {source} [LATENCY] {latency:.2f}s")
        else:
            print(json.dumps({"triggered": False}))
            sys.stdout.flush()

    runtime = time.time() - start_time
    print(json.dumps({"session_end": True, "verses_triggered": verses_count, "runtime_seconds": int(runtime)}))
    sys.stdout.flush()
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
        # In test mode, we want to process EVERYTHING to verify accuracy.
        # We use the standard queue.put() which blocks if the queue is full.
        audio_queue.put(window.copy())
        ptr += STEP_SAMPLES
        
    logger.info("Test file queued for processing.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MultiVerse Backend")
    parser.add_argument("--test-file", help="Path to a WAV file to process instead of live mic")
    args = parser.parse_args()

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
