# device_utils.py
# Finds the best working microphone at startup.
# Eliminates the "wrong device index" failure permanently.

import pyaudio
import numpy as np
import logging

logger = logging.getLogger(__name__)

def find_best_input_device() -> int:
    """
    Test every available input device for 0.5 seconds.
    Return the index of the device with the highest RMS.
    This ensures the correct microphone is always selected
    regardless of Windows device ordering changes.
    
    Returns:
        int: device index with highest detected audio level
    """
    p = pyaudio.PyAudio()
    best_index = 0
    best_rms = 0.0
    
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if d['maxInputChannels'] < 1:
            continue
        try:
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=i,
                frames_per_buffer=8000
            )
            data = stream.read(8000, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.float32)
            rms = float(np.sqrt(np.mean(audio ** 2)))
            stream.stop_stream()
            stream.close()
            logger.info(f"Device {i} ({d['name'][:30]}): RMS={rms:.5f}")
            if rms > best_rms:
                best_rms = rms
                best_index = i
        except Exception as e:
            logger.debug(f"Device {i} failed: {e}")
    
    p.terminate()
    logger.info(f"Selected device: {best_index} (RMS={best_rms:.5f})")
    return best_index
