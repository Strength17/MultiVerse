# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import faiss
import pickle
import configparser
import logging
import os
import time
from typing import Optional, Dict
from sentence_transformers import SentenceTransformer

# path/to/project_config.md - Section 6 (UPDATED)
BOOK_NUMBER_TO_CANONICAL = {
    10: "Genesis", 20: "Exodus", 30: "Leviticus", 40: "Numbers", 50: "Deuteronomy",
    60: "Joshua", 70: "Judges", 80: "Ruth", 90: "1 Samuel", 100: "2 Samuel",
    110: "1 Kings", 120: "2 Kings", 130: "1 Chronicles", 140: "2 Chronicles",
    150: "Ezra", 160: "Nehemiah", 190: "Esther", 220: "Job", 230: "Psalms",
    240: "Proverbs", 250: "Ecclesiastes", 260: "Song of Solomon", 290: "Isaiah",
    300: "Jeremiah", 310: "Lamentations", 330: "Ezekiel", 340: "Daniel",
    350: "Hosea", 360: "Joel", 370: "Amos", 380: "Obadiah", 390: "Jonah",
    400: "Micah", 410: "Nahum", 420: "Habakkuk", 430: "Zephaniah", 440: "Haggai",
    450: "Zechariah", 460: "Malachi", 470: "Matthew", 480: "Mark", 490: "Luke",
    500: "John", 510: "Acts", 520: "Romans", 530: "1 Corinthians",
    540: "2 Corinthians", 550: "Galatians", 560: "Ephesians", 570: "Philippians",
    580: "Colossians", 590: "1 Thessalonians", 600: "2 Thessalonians",
    610: "1 Timothy", 620: "2 Timothy", 630: "Titus", 640: "Philemon",
    650: "Hebrews", 660: "James", 670: "1 Peter", 680: "2 Peter", 690: "1 John",
    700: "2 John", 710: "3 John", 720: "Jude", 730: "Revelation",
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
config = configparser.ConfigParser()
config.read('config.ini')
INDEX_PATH = config.get('vectors', 'index_path', fallback='data/bible_vectors.index')
MAP_PATH = config.get('vectors', 'verse_map_path', fallback='data/bible_verse_map.pkl')
MODEL_NAME = config.get('vectors', 'embedding_model', fallback='all-MiniLM-L6-v2')
DEFAULT_THRESHOLD = float(config.get('detection', 'vector_threshold', fallback=0.72))

# Global variables for model and index
_model = None
_index = None
_verse_map = None

def load_resources():
    """
    Loads FAISS index and verse map into memory.
    """
    global _model, _index, _verse_map
    
    start_time = time.time()
    logger.info(f"Loading vector search resources from {INDEX_PATH}")
    
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAP_PATH):
        logger.error("Vector index or map files missing. Run build_vector_db.py first.")
        return False

    try:
        _model = SentenceTransformer(MODEL_NAME)
        _index = faiss.read_index(INDEX_PATH)
        with open(MAP_PATH, 'rb') as f:
            _verse_map = pickle.load(f)
            
        load_time = time.time() - start_time
        logger.info(f"Vector search resources loaded in {load_time:.2f}s")
        return True
    except Exception as e:
        logger.error(f"Error loading vector resources: {e}")
        return False

# Load resources at import time
if not load_resources():
    logger.warning("Vector search initialization failed.")

def search_paraphrase(text: str, threshold: Optional[float] = None) -> Optional[dict]:
    """
    Encodes query text and searches the FAISS index for the closest verse.
    """
    if _index is None or _model is None or _verse_map is None:
        return None
        
    if threshold is None:
        threshold = DEFAULT_THRESHOLD

    try:
        # Encode and normalize query
        query_vec = _model.encode([text], convert_to_numpy=True)
        faiss.normalize_L2(query_vec)
        
        # Search top-1
        scores, indices = _index.search(query_vec, 1)
        
        score = float(scores[0][0])
        idx = int(indices[0][0])
        
        if score >= threshold:
            verse_info = _verse_map[idx]
            book_id = verse_info['book_id']
            return {
                "book_id": book_id,
                "book": BOOK_NUMBER_TO_CANONICAL[book_id],
                "chapter": verse_info['chapter'],
                "verse": verse_info['verse'],
                "score": score
            }
    except Exception as e:
        logger.error(f"Search error: {e}")
        
    return None

if __name__ == '__main__':
    # Test Phase 3B verification
    test_query = "no more condemnation"
    res = search_paraphrase(test_query, 0.72)
    if res:
        print(f"PASS: Found {res['book']} {res['chapter']}:{res['verse']} with score {res['score']:.4f}")
    else:
        print("FAIL: No match found.")
