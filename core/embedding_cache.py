# core/embedding_cache.py

import os
import pickle
import numpy as np
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from core.bible_db import BibleDB, build_ref

logger = logging.getLogger(__name__)

class EmbeddingLoader(QObject):
    """Pre-computes all verse embeddings at startup. Runs once."""
    progress = pyqtSignal(int)
    ready = pyqtSignal(object, object, list)  # (model, matrix, refs)

    def __init__(self, db_path: str, model_cache: str, cache_dir: str = 'data/'):
        super().__init__()
        self.db_path = db_path
        self.model_cache = model_cache
        self.cache_dir = cache_dir
        self.matrix_path = os.path.join(cache_dir, 'verse_embeddings.npy')
        self.refs_path = os.path.join(cache_dir, 'verse_refs.pkl')

    def run(self) -> None:
        """Loads embeddings from cache or computes if missing/invalid."""
        # Check for DB early
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        from sentence_transformers import SentenceTransformer
        
        # Check if cache is valid
        if os.path.exists(self.matrix_path) and os.path.exists(self.refs_path):
            logger.info("Loading embeddings from cache.")
            matrix = np.load(self.matrix_path)
            with open(self.refs_path, 'rb') as f:
                refs = pickle.load(f)
            # Need to re-load model but not compute
            model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=self.model_cache, local_files_only=True)
            self.ready.emit(model, matrix, refs)
            return

        logger.info("Computing verse embeddings...")
        model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=self.model_cache, local_files_only=True)
        
        db = BibleDB(self.db_path)
        with db._get_connection() as conn:
            cursor = conn.execute("SELECT Book, Chapter, VerseNumber, Verse FROM bible")
            rows = cursor.fetchall()
            
        texts = [r[3] for r in rows]
        refs = [build_ref(r[0], r[1], r[2]) for r in rows]
        
        batch_size = 1000
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            emb = model.encode(batch, convert_to_numpy=True, normalize_embeddings=True)
            all_embeddings.append(emb)
            self.progress.emit(int((i / len(texts)) * 100))
        
        matrix = np.vstack(all_embeddings)
        
        # Save cache
        os.makedirs(self.cache_dir, exist_ok=True)
        np.save(self.matrix_path, matrix)
        with open(self.refs_path, 'wb') as f:
            pickle.dump(refs, f)
            
        self.ready.emit(model, matrix, refs)
