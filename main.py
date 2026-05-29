# main.py
import sys
import time
import queue
import threading
import logging
import configparser
import numpy as np
import json
import collections

from verse_detector import detect_explicit
from bible_db import get_verse
from vector_search import search_paraphrase
from transcriber import transcribe_chunk
from device_utils import find_best_input_device

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.FileHandler("logs/multiverse.log"), logging.StreamHandler(sys.stderr)])
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

SAMPLE_RATE = config.getint('audio', 'sample_rate', fallback=16000)
CHUNK_SECONDS = config.getfloat('audio', 'chunk_seconds', fallback=3.0)
OVERLAP_SECONDS = config.getfloat('audio', 'overlap_seconds', fallback=1.5)
CHUNK_SAMPLES = int(CHUNK_SECONDS * SAMPLE_RATE)
STEP_SAMPLES = int((CHUNK_SECONDS - OVERLAP_SECONDS) * SAMPLE_RATE)
VAD_THRESHOLD = config.getfloat('audio', 'vad_rms_threshold', fallback=0.0005)

audio_queue = queue.Queue(maxsize=1)
running = True

def process_audio():
    transcript_buffer = collections.deque(maxlen=2)
    cooldown = {}
    
    while running or not audio_queue.empty():
        try: item = audio_queue.get(timeout=1.0)
        except queue.Empty: continue
        
        if item is None:
            transcript_buffer.clear()
            continue
        
        t_start = time.time()
        transcript = transcribe_chunk(item)
        print(f"[TRANSCRIPT] {transcript}", file=sys.stderr)
        transcript_buffer.append(transcript)
        text = ' '.join(transcript_buffer)

        # Detection
        match = detect_explicit(text) or search_paraphrase(text)
            
        if match:
            key = (match.get('book'), match.get('chapter'), match.get('verse'))
            if time.time() - cooldown.get(key, 0) > 8:
                verse = get_verse(match.get('book'), match.get('chapter'), match.get('verse'))
                if verse:
                    cooldown[key] = time.time()
                    print(json.dumps({**verse, "triggered": True, "latency_ms": int((time.time()-t_start)*1000)}), flush=True)
        audio_queue.task_done()

def run_live():
    import pyaudio
    p = pyaudio.PyAudio()
    
    dev_cfg = config.get('audio', 'input_device_index', fallback='1')
    device_index = int(dev_cfg)
    logger.info(f"Using device index: {device_index}")
    
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=SAMPLE_RATE, input=True, input_device_index=device_index, frames_per_buffer=1024)
    buffer = np.array([], dtype=np.float32)
    
    while running:
        data = stream.read(1024, exception_on_overflow=False)
        audio_chunk = np.frombuffer(data, dtype=np.float32)
        
        # Check for bad data
        if np.isnan(audio_chunk).any() or np.isinf(audio_chunk).any():
            continue
            
        buffer = np.concatenate([buffer, audio_chunk])
        while len(buffer) >= CHUNK_SAMPLES:
            window = buffer[:CHUNK_SAMPLES]
            buffer = buffer[STEP_SAMPLES:]
            
            if np.sqrt(np.mean(window ** 2)) < VAD_THRESHOLD:
                try: audio_queue.put_nowait(None)
                except: pass
                continue
            try: audio_queue.put_nowait(window)
            except: pass
    stream.close()

if __name__ == '__main__':
    threading.Thread(target=process_audio, daemon=True).start()
    print("MultiVerse v2.2.0 — Live Pipeline")
    run_live()
