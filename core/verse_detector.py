# core/verse_detector.py
import re
import logging
import numpy as np
from typing import Optional, List, Dict
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from rapidfuzz import process, fuzz
from data.book_names import BIBLE_BOOKS
from utils.number_words import text_to_number
from core.bible_db import BibleDB

logger = logging.getLogger(__name__)

class DetectionWorker(QObject):
    """Runs on a QThread. Receives transcript chunks, emits detected verses."""
    
    verse_detected = pyqtSignal(dict)
    
    def __init__(self, model, embeddings, refs, config):
        super().__init__()
        self._model = model
        self._embeddings = embeddings
        self._refs = refs
        self._config = config
        self._threshold = float(config["detection"]["confidence_threshold"])
        self._detector = VerseDetector(confidence_threshold=self._threshold)
        
        # Sliding window buffer: last 15 seconds of transcript
        self._buffer = []
        self._buffer_window = 15
    
    @pyqtSlot(str, float)
    def process_chunk(self, text: str, timestamp: float) -> None:
        """Called for each Whisper chunk. Runs both detection tiers."""
        self._buffer.append((timestamp, text))
        cutoff = timestamp - self._buffer_window
        self._buffer = [(t, x) for t, x in self._buffer if t >= cutoff]
        window_text = " ".join(x for _, x in self._buffer)
        
        # Tier 1 — Reference Detection (fast regex)
        matches = self._detector.detect(window_text)
        for match in matches:
            if match["confidence"] >= self._threshold:
                with BibleDB() as db:
                    verse = db.lookup_verse(match["book"], match["chapter"], match["verse"])
                    if verse:
                        self.verse_detected.emit({**match, "verse_text": verse, "reference": f"{match['book']} {match['chapter']}:{match['verse']}", "method": "reference"})
                        return
        
        # Tier 2 — Semantic Similarity
        query_emb = self._model.encode(
            [window_text[-500:]],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        scores = np.dot(self._embeddings, query_emb[0])
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        
        if best_score >= self._threshold:
            ref = self._refs[best_idx]
            with BibleDB() as db:
                verse_text = db.lookup_verse(*self._parse_ref(ref))
                self.verse_detected.emit({
                    "verse_text": verse_text,
                    "reference": ref,
                    "confidence": best_score,
                    "method": "semantic",
                    "matched_phrase": window_text[-100:],
                })

    def _parse_ref(self, ref: str):
        # Helper to convert "Book Chapter:Verse" to (Book, Chapter, Verse)
        parts = ref.replace(":", " ").split()
        return parts[0], int(parts[1]), int(parts[2])

class VerseDetector:
    """Detects Bible verse references using Tier 1 (regex)."""

    def __init__(self, confidence_threshold: float = 0.50):
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
        if not val: return None
        if val.isdigit(): return int(val)
        return text_to_number(val)

    def detect(self, text: str) -> List[Dict]:
        detections = []
        for match in self.ref_pattern.finditer(text):
            raw_book = match.group('book').strip().lower()
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
                    })
        return detections
