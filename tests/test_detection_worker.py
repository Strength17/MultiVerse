# tests/test_detection_worker.py
import pytest
from core.verse_detector import DetectionWorker

def test_parse_ref_utility(test_config, mock_embeddings):
    matrix, refs = mock_embeddings
    worker = DetectionWorker(None, matrix, refs, test_config)
    assert worker._parse_ref("John 3:16") == ("John", 3, 16)

def test_detection_worker_initialization(test_config, mock_embeddings):
    matrix, refs = mock_embeddings
    worker = DetectionWorker(None, matrix, refs, test_config)
    assert worker._threshold == 0.50
    assert worker._buffer_window == 15
