# utils/number_words.py
from word2number import w2n
import logging

logger = logging.getLogger(__name__)

def text_to_number(text: str) -> int:
    """
    Converts spoken number words into an integer.
    
    Args:
        text: The string containing the spoken number (e.g., "three sixteen").
        
    Returns:
        The integer representation, or None if conversion fails.
    """
    try:
        return w2n.word_to_num(text)
    except Exception as e:
        logger.debug(f"Could not convert '{text}' to number: {e}")
        return None
