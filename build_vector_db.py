# build_vector_db.py

import sqlite3
import pickle
import faiss
import numpy as np
import configparser
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os

# Load config
config = configparser.ConfigParser()
config.read('config.ini')
db_path = 'data/NKJV.SQLite3'

def build():
    """
    Builds the FAISS vector database from the SQLite NKJV Bible in batches.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT book_number, chapter, verse, text FROM verses")
    rows = cursor.fetchall()
    
    mapping = [{'book_id': row[0], 'chapter': row[1], 'verse_num': row[2]} for row in rows]
    texts = [row[3] for row in rows]
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    dimension = 384
    index = faiss.IndexFlatIP(dimension)
    
    batch_size = 100
    for i in tqdm(range(0, len(texts), batch_size), desc="Encoding"):
        batch_texts = texts[i : i + batch_size]
        embeddings = model.encode(batch_texts, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
    
    faiss.write_index(index, 'data/bible_vectors.index')
    with open('data/bible_verse_map.pkl', 'wb') as f:
        pickle.dump(mapping, f)
        
    print("Vector database built successfully.")
    conn.close()

if __name__ == '__main__':
    build()
