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
        logging.StreamHandler(sys.stderr) 
    ]
)
logger = logging.getLogger(__name__)

# Load config
config = configparser.ConfigParser()
config.read('config.ini')

SAMPLE_RATE = config.getint('audio', 'sample_rate', fallback=16000)
CHUNK_SECONDS = config.getfloat('audio', 'chunk_seconds', fallback=3.0)
OVERLAP_SECONDS = config.getfloat('audio', 'overlap_seconds', fallback=0.0)
CHANNELS = config.getint('audio', 'channels', fallback=1)
vad_rms_threshold = config.getfloat('audio', 'vad_rms_threshold', fallback=0.015)
MAX_QUEUE_SIZE = config.getint('audio', 'max_queue_size', fallback=1)

CHUNK_SAMPLES = int(CHUNK_SECONDS * SAMPLE_RATE)

# Global state
audio_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
is_running = True

def signal_handler(sig, frame):
    global is_running
    is_running = False

signal.signal(signal.SIGINT, signal_handler)

def process_audio_thread():
    """
    Main processing loop. Runs transcription and detection sequentially.
    """
    transcript_buffer = deque(maxlen=2)
    logger.info("Transcript buffer initialised: depth=2")

    while is_running or not audio_queue.empty():
        try:
            window = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # VAD gate
        rms = float(np.sqrt(np.mean(window ** 2)))
        if rms < vad_rms_threshold:
            audio_queue.task_done()
            continue

        t_start = time.time()
        transcript = transcribe_chunk(window)
        transcript_buffer.append(transcript)
        text = ' '.join(transcript_buffer)

        match = detect_explicit(text)
        if not match:
            match = search_paraphrase(text)
            
        if match:
            verse = get_verse(match['book'], match['chapter'], match.get('verse'))
            latency = time.time() - t_start
            if verse:
                print(json.dumps({
                    **verse,
                    "triggered": True,
                    "latency_ms": int(latency * 1000),
                    "transcript": {"current": transcript, "full": text}
                }))
                logger.info(f"TRIGGERED: {verse['book']} {verse['chapter']}:{verse['verse']} (latency {latency:.2f}s)")
        
        audio_queue.task_done()

def run_live():
    import pyaudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=1024)
    audio_buffer = np.array([], dtype=np.float32)
    while is_running:
        data = stream.read(1024, exception_on_overflow=False)
        audio_buffer = np.concatenate([audio_buffer, np.frombuffer(data, dtype=np.float32)])
        if len(audio_buffer) >= CHUNK_SAMPLES:
            window = audio_buffer[:CHUNK_SAMPLES]
            audio_buffer = audio_buffer[CHUNK_SAMPLES:]
            try:
                audio_queue.put_nowait(window)
            except queue.Full:
                # Drop old chunk, insert new
                try: audio_queue.get_nowait()
                except: pass
                audio_queue.put_nowait(window)
    stream.stop_stream()
    stream.close()
    p.terminate()

def run_test_file(file_path):
    import librosa
    audio, _ = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    ptr = 0
    while ptr + CHUNK_SAMPLES <= len(audio):
        audio_queue.put(audio[ptr : ptr + CHUNK_SAMPLES].copy())
        ptr += CHUNK_SAMPLES
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-file")
    args = parser.parse_args()

    # Pre-warm
    import numpy as np
    transcribe_chunk(np.zeros(16000, dtype=np.float32))
    search_paraphrase("God so loved the world")

    proc_thread = threading.Thread(target=process_audio_thread, daemon=True)
    proc_thread.start()

    if args.test_file:
        run_test_file(args.test_file)
        time.sleep(5)
        is_running = False
    else:
        run_live()
    proc_thread.join()
