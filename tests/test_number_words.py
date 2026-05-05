# tests/test_number_words.py
import pytest
from utils.number_words import text_to_number

def test_single_numbers():
    assert text_to_number("one") == 1
    assert text_to_number("five") == 5
    assert text_to_number("ten") == 10

def test_compound_numbers():
    assert text_to_number("twenty eight") == 28
    assert text_to_number("one hundred") == 100
    assert text_to_number("three hundred sixteen") == 316
    assert text_to_number("one thousand two hundred thirty four") == 1234

def test_invalid_input():
    assert text_to_number("not a number") is None
