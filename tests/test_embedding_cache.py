# tests/test_embedding_cache.py
import os
import numpy as np
import pytest
import pickle
from core.embedding_cache import EmbeddingLoader

def test_embedding_cache_paths(test_config):
    loader = EmbeddingLoader("data/test.db", "cache_model", "cache/")
    assert loader.matrix_path == os.path.join("cache/", "verse_embeddings.npy")
    assert loader.refs_path == os.path.join("cache/", "verse_refs.pkl")

def test_embedding_cache_invalid_path():
    with pytest.raises(Exception):
        loader = EmbeddingLoader("nonexistent.db", "cache_model", "cache/")
        loader.run()
