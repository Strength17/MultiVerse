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
import collections

from transcriber import transcribe_chunk
from device_utils import find_best_input_device

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("logs/multiverse.log"), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

SAMPLE_RATE = config.getint('audio', 'sample_rate', fallback=16000)
CHUNK_SECONDS = config.getfloat('audio', 'chunk_seconds', fallback=3.0)
CHUNK_SAMPLES = int(CHUNK_SECONDS * SAMPLE_RATE)
VAD_THRESHOLD = config.getfloat('audio', 'vad_rms_threshold', fallback=0.0005)

audio_queue = queue.Queue(maxsize=1)
running = True

def process_audio():
    transcript_buffer = collections.deque(maxlen=2)
    while running or not audio_queue.empty():
        try:
            item = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue
        if item is None:
            transcript_buffer.clear()
            continue
        
        t_start = time.time()
        transcript = transcribe_chunk(item)
        logger.info(f"Transcript: '{transcript}' ({time.time()-t_start:.2f}s)")
        transcript_buffer.append(transcript)
        
        # Phase 1: Only print transcript
        print(json.dumps({"triggered": False, "transcript": {"current": transcript, "full_window": ' '.join(transcript_buffer)}}), flush=True)
        audio_queue.task_done()

def run_live():
    import pyaudio
    p = pyaudio.PyAudio()
    
    dev_cfg = config.get('audio', 'input_device_index', fallback='auto')
    device_index = find_best_input_device() if dev_cfg == 'auto' else int(dev_cfg)
    
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=SAMPLE_RATE, input=True, input_device_index=device_index, frames_per_buffer=1024)
    buffer = np.array([], dtype=np.float32)
    
    while running:
        data = stream.read(1024, exception_on_overflow=False)
        buffer = np.concatenate([buffer, np.frombuffer(data, dtype=np.float32)])
        
        if len(buffer) >= CHUNK_SAMPLES:
            window = buffer[:CHUNK_SAMPLES]
            buffer = buffer[CHUNK_SAMPLES:]
            
            rms = float(np.sqrt(np.mean(window ** 2)))
            if rms < VAD_THRESHOLD:
                try: audio_queue.put_nowait(None)
                except: pass
                continue
            
            try: audio_queue.put_nowait(window)
            except queue.Full:
                try: audio_queue.get_nowait()
                except: pass
                audio_queue.put_nowait(window)

if __name__ == '__main__':
    threading.Thread(target=process_audio, daemon=True).start()
    print("MultiVerse v1.0.0 — Live")
    run_live()
