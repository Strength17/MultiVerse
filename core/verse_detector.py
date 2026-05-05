# core/verse_detector.py
import re
import logging
from typing import Optional, List, Dict
from rapidfuzz import process, fuzz
from data.book_names import BIBLE_BOOKS
from utils.number_words import text_to_number

logger = logging.getLogger(__name__)

class VerseDetector:
    """
    Detects Bible verse references in transcribed text.
    Uses regex for structure detection and fuzzy matching for book names.
    """

    def __init__(self, confidence_threshold: float = 0.70):
        """
        Initializes the VerseDetector.
        """
        self.confidence_threshold = confidence_threshold
        self.all_variants = {}
        for book, variants in BIBLE_BOOKS.items():
            for v in variants:
                self.all_variants[v] = book
        
        self.ref_pattern = re.compile(
            r'(?P<book>[\w\s]+?)\s+(?:chapter\s+)?(?P<chapter>\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty-eight|twenty-three)\s*(?::|verse|v)?\s*(?P<verse>\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty-eight|twenty-three)?',
            re.IGNORECASE
        )

    def _normalize_number(self, val: Optional[str]) -> Optional[int]:
        """Converts digit strings or word numbers to integers."""
        if not val:
            return None
        if val.isdigit():
            return int(val)
        return text_to_number(val)

    def detect(self, text: str) -> List[Dict]:
        """
        Detects potential verse references with confidence scoring.
        """
        detections = []
        for match in self.ref_pattern.finditer(text):
            raw_book = match.group('book').strip().lower()
            logger.debug(f"Detected potential ref: {match.groups()}")
            
            # Fuzzy match
            best_match = process.extractOne(raw_book, self.all_variants.keys(), scorer=fuzz.WRatio)
            
            if best_match and (best_match[1] / 100) >= self.confidence_threshold:
                chapter = self._normalize_number(match.group('chapter'))
                verse = self._normalize_number(match.group('verse'))
                
                if chapter is not None:
                    detections.append({
                        'book': self.all_variants[best_match[0]],
                        'chapter': chapter,
                        'verse': verse,
                        'confidence': best_match[1] / 100,
                        'raw': match.group(0)
                    })
        return detections
