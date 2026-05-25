# build_vector_db.py

import sqlite3
import pickle
import numpy as np
import faiss
import configparser
import logging
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
config = configparser.ConfigParser()
config.read('config.ini')
DB_PATH = config.get('database', 'db_path', fallback='data/NKJV.SQLite3')
INDEX_PATH = config.get('vectors', 'index_path', fallback='data/bible_vectors.index')
MAP_PATH = config.get('vectors', 'verse_map_path', fallback='data/bible_verse_map.pkl')
MODEL_NAME = config.get('vectors', 'embedding_model', fallback='all-MiniLM-L6-v2')

def clean_verse_text(raw: str) -> str:
    """
    Strips HTML-like markup from raw verse text.
    Copied from bible_db.py to ensure consistency.
    """
    text = re.sub(r'<f>\[.*?†\]</f>', '', raw)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_index():
    """
    Reads all verses, encodes them, and saves the FAISS index.
    """
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    verses_data = []
    texts_to_encode = []
    
    logger.info(f"Reading verses from {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT book_number, chapter, verse, text FROM verses")
        rows = cursor.fetchall()
        
        for row in tqdm(rows, desc="Cleaning verses"):
            book_num, chapter, verse_num, raw_text = row
            clean_text = clean_verse_text(raw_text)
            if clean_text:
                texts_to_encode.append(clean_text)
                verses_data.append({
                    "book_id": book_num,
                    "chapter": chapter,
                    "verse": verse_num
                })
                
    logger.info(f"Encoding {len(texts_to_encode)} verses. This may take a while on this CPU...")
    # Encode in batches to avoid OOM and show progress
    embeddings = model.encode(
        texts_to_encode, 
        batch_size=128, 
        show_progress_bar=True, 
        convert_to_numpy=True
    )
    
    logger.info("Normalizing vectors for cosine similarity (Inner Product)")
    faiss.normalize_L2(embeddings)
    
    logger.info("Creating FAISS index")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    logger.info(f"Saving index to {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)
    
    logger.info(f"Saving verse map to {MAP_PATH}")
    with open(MAP_PATH, 'wb') as f:
        pickle.dump(verses_data, f)
        
    logger.info("Index build complete.")
    
    # Self-test
    logger.info("Running self-test...")
    query = "there is no condemnation for those in Christ"
    query_vec = model.encode([query])
    faiss.normalize_L2(query_vec)
    
    scores, indices = index.search(query_vec, 3)
    
    print("\nSelf-Test Results (Top 3):")
    for i in range(3):
        idx = indices[0][i]
        score = scores[0][i]
        v = verses_data[idx]
        print(f"[{i+1}] Score: {score:.4f} | Book ID: {v['book_id']} | Chap: {v['chapter']} | Verse: {v['verse']}")
        
    # Check if Romans 8:1 (Book ID 520) is in top 3
    found = False
    for j in range(3):
        if verses_data[indices[0][j]]['book_id'] == 520 and \
           verses_data[indices[0][j]]['chapter'] == 8 and \
           verses_data[indices[0][j]]['verse'] == 1:
            found = True
            break
            
    if found:
        print("\nSUCCESS: Romans 8:1 found in top 3 results.")
    else:
        print("\nWARNING: Romans 8:1 NOT found in top 3 results.")

if __name__ == '__main__':
    build_index()
