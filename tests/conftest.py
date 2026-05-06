# tests/conftest.py
import pytest
import os
import configparser
from core.bible_db import BibleDB
import numpy as np

# Force offline mode for all tests
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

@pytest.fixture
def test_config():
    config = configparser.ConfigParser()
    config['database'] = {'db_path': 'data/KJVBible_Database.db'}
    config['detection'] = {'confidence_threshold': '0.50'}
    config['display'] = {'background_color': '#000000', 'fade_in_ms': '500', 'fade_out_ms': '500', 'fullscreen': 'false'}
    return config

@pytest.fixture
def db_conn(test_config):
    db = BibleDB(test_config['database']['db_path'])
    return db

@pytest.fixture
def mock_embeddings():
    # Return a dummy 5x384 matrix and 5 refs for testing
    matrix = np.random.rand(5, 384).astype(np.float32)
    refs = ["Gen 1:1", "Gen 1:2", "John 3:16", "Rom 8:28", "Psalm 23:1"]
    return matrix, refs
