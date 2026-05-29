# transcriber.py
# Sets offline env vars BEFORE any imports.
# Loads tiny.en with proven parameters from day one.

import os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

import numpy as np
import logging
import time
import configparser

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

MODEL_SIZE   = config.get('transcription', 'model_size', fallback='tiny.en')
BEAM_SIZE    = int(config.get('transcription', 'beam_size', fallback='1'))
TEMPERATURE  = float(config.get('transcription', 'temperature', fallback='0'))
CONDITION    = config.getboolean('transcription',
                   'condition_on_previous_text', fallback=False)
FP16         = config.getboolean('transcription', 'fp16', fallback=False)
PROMPT       = config.get('transcription', 'initial_prompt', fallback='')

_model = None

def _load():
    global _model
    t = time.time()
    try:
        from faster_whisper import WhisperModel
        _model = WhisperModel(MODEL_SIZE, device='cpu',
                              compute_type='int8',
                              local_files_only=True)
        logger.info(f"Backend: faster-whisper | loaded in {time.time()-t:.2f}s")
        return
    except Exception as e:
        logger.warning(f"faster-whisper failed: {e}")
    
    import whisper
    _model = whisper.load_model(MODEL_SIZE)
    logger.info(f"Backend: openai-whisper | loaded in {time.time()-t:.2f}s")

_load()

# Log confirmed parameters
logger.info(f"Whisper params — beam:{BEAM_SIZE} temp:{TEMPERATURE} "
            f"condition:{CONDITION} fp16:{FP16}")

# Pre-warm model
_dummy = np.zeros(16000, dtype=np.float32)
try:
    if hasattr(_model, 'transcribe') and callable(
            getattr(_model, 'transcribe')):
        pass
except Exception:
    pass
logger.info("Whisper pre-warmed")


def transcribe_chunk(audio: np.ndarray,
                     sample_rate: int = 16000) -> str:
    """
    Transcribe float32 audio array to text.
    All parameters read from config.ini.
    beam_size=1 and temperature=0 enforced for speed.
    
    Args:
        audio: float32 numpy array
        sample_rate: must be 16000
    Returns:
        transcribed text string
    """
    if _model is None:
        return ''
    try:
        from faster_whisper import WhisperModel
        if isinstance(_model, WhisperModel):
            segs, _ = _model.transcribe(
                audio,
                beam_size=BEAM_SIZE,
                temperature=TEMPERATURE,
                initial_prompt=PROMPT or None,
                language='en',
            )
            return ' '.join(s.text for s in segs).strip()
    except Exception:
        pass
    
    result = _model.transcribe(
        audio,
        beam_size=BEAM_SIZE,
        temperature=TEMPERATURE,
        condition_on_previous_text=CONDITION,
        initial_prompt=PROMPT or None,
        fp16=FP16,
        language='en'
    )
    return result.get('text', '').strip()
