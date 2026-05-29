# vector_search.py
# Implements semantic verse detection using FAISS + SentenceTransformers.

import os
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import faiss
import pickle
import logging
import configparser
from typing import Optional, Dict
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')
INDEX_PATH = config.get('vectors', 'index_path', fallback='data/bible_vectors.index')
MAP_PATH = config.get('vectors', 'verse_map_path', fallback='data/bible_verse_map.pkl')
MODEL_NAME = config.get('vectors', 'embedding_model', fallback='all-MiniLM-L6-v2')
THRESHOLD = config.getfloat('detection', 'vector_threshold', fallback=0.70)

_model = SentenceTransformer(MODEL_NAME)
_index = faiss.read_index(INDEX_PATH, faiss.IO_FLAG_MMAP)
with open(MAP_PATH, 'rb') as f:
    _verse_map = pickle.load(f)

def search_paraphrase(text: str, threshold: float = THRESHOLD) -> Optional[Dict]:
    """
    Search index for semantic matches.
    """
    try:
        vec = _model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        scores, indices = _index.search(vec, 1)
        if scores[0][0] >= threshold:
            idx = int(indices[0][0])
            verse_info = _verse_map[idx]
            return {
                "book_id": verse_info['book_id'],
                "chapter": verse_info['chapter'],
                "verse": verse_info['verse_num'],
                "score": float(scores[0][0])
            }
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
    return None
