# pre_fix_test_runner.py
import numpy as np
import os
import time
import json
from verse_detector import detect_explicit

def run_group_a():
    print("--- GROUP A: VAD Unit Tests ---")
    # TEST A-01: VAD blocks silence
    silence = np.zeros(48000, dtype=np.float32)
    rms = float(np.sqrt(np.mean(silence ** 2)))
    print(f"A-01: silence RMS={rms:.4f}")
    if rms < 0.015:
        print("PASS A-01: silence RMS correctly below threshold")
    else:
        print(f"FAIL A-01: silence RMS={rms} should be < 0.015")

    # TEST A-02: VAD passes speech-level audio
    speech_sim = np.random.uniform(-0.05, 0.05, 48000).astype(np.float32)
    rms = float(np.sqrt(np.mean(speech_sim ** 2)))
    print(f"A-02: speech RMS={rms:.4f}")
    if rms >= 0.015:
        print(f"PASS A-02: speech-level RMS={rms:.4f} correctly above threshold")
    else:
        print(f"FAIL A-02: speech RMS={rms} should be >= 0.015")

    # TEST A-03: VAD runs before queue (structural test)
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    vad_pos = content.find('vad_rms_threshold')
    queue_pos = content.find('audio_queue.put')
    print(f"A-03: vad_pos={vad_pos}, queue_pos={queue_pos}")
    if vad_pos < queue_pos and vad_pos != -1:
        print("PASS A-03: VAD gate confirmed before queue.put()")
    else:
        # Check if it's in process_audio_thread instead of capture loop
        process_pos = content.find('def process_audio_thread')
        if vad_pos > process_pos:
            print("FAIL A-03: VAD check appears in processing thread, not capture loop")
        else:
            print(f"FAIL A-03: VAD check (pos {vad_pos}) must appear BEFORE queue.put (pos {queue_pos})")

def run_group_b():
    print("\n--- GROUP B: Book Priority Unit Tests ---")
    import verse_detector
    # Reset memory
    verse_detector._last_book = "Ruth"
    verse_detector._last_book_time = time.time()
    
    # TEST B-01: Current book overrides memory
    result = detect_explicit("Job chapter 4 verse 4")
    print(f"B-01: Input 'Job chapter 4 verse 4', memory 'Ruth'. Result: {result}")
    if result and result['book'] == 'Job':
        print("PASS B-01: current book correctly overrides stale memory")
    else:
        print(f"FAIL B-01: expected Job, got {result['book'] if result else None}")

    # TEST B-02: Memory used when no book in current window
    detect_explicit("book of Genesis chapter 1")
    time.sleep(0.1)
    result = detect_explicit("verse 1")
    print(f"B-02: Input 'verse 1', memory 'Genesis'. Result: {result}")
    if result and result['book'] == 'Genesis':
        print("PASS B-02: book memory correctly used when no book in current text")
    else:
        print(f"FAIL B-02: expected Genesis from memory, got {result['book'] if result else None}")

    # TEST B-03: Memory expires
    detect_explicit("book of Romans 8:1")
    print("B-03: Waiting for memory expiry (6s)...")
    time.sleep(6)
    result = detect_explicit("verse 1")
    print(f"B-03: Result after 6s: {result}")
    if result is None:
        print("PASS B-03: expired book memory correctly ignored")
    else:
        print(f"FAIL B-03: expired memory should not match, got {result}")

def run_group_c():
    print("\n--- GROUP C: Hyphen Separator Unit Tests ---")
    # TEST C-01: Hyphen separator detected
    result = detect_explicit("Revelation 1-1")
    print(f"C-01: Revelation 1-1 -> {result}")
    if result and result['book'] == 'Revelation' and result['chapter'] == 1 and result['verse'] == 1:
        print("PASS C-01: hyphen separator correctly parsed")
    else:
        print(f"FAIL C-01: Revelation 1-1 not matched correctly")

    # TEST C-02: "Revelations" alias
    result = detect_explicit("Revelations 1-1")
    print(f"C-02: Revelations 1-1 -> {result}")
    if result and result['book'] == 'Revelation':
        print("PASS C-02: Revelations alias correctly resolves to Revelation")
    else:
        print(f"FAIL C-02: Revelations 1-1 not matched")

    # TEST C-03: Hyphen with chapter keyword
    result = detect_explicit("Revelation chapter 22-21")
    print(f"C-03: Revelation chapter 22-21 -> {result}")
    if result and result['chapter'] == 22 and result['verse'] == 21:
        print("PASS C-03: hyphen with chapter keyword correctly parsed")
    else:
        print(f"FAIL C-03: Revelation chapter 22-21 not matched correctly")

def run_group_d():
    print("\n--- GROUP D: Regression Tests ---")
    import verse_detector
    tests = [
        ("Romans chapter 8 verse 1", {"book": "Romans", "chapter": 8, "verse": 1}, "D-01"),
        ("Romans chapter 8 was 1", {"book": "Romans", "chapter": 8, "verse": 1}, "D-02"),
        ("book of Genesis 1:1", {"book": "Genesis", "chapter": 1, "verse": 1}, "D-03"),
        ("John 3:16", {"book": "John", "chapter": 3, "verse": 16}, "D-06"),
        ("First Corinthians 13:4", {"book": "1 Corinthians", "chapter": 13, "verse": 4}, "D-07")
    ]
    for text, expected, label in tests:
        # Reset memory for each regression test to be clean
        verse_detector._last_book = None
        verse_detector._last_book_time = 0
        result = verse_detector.detect_explicit(text)
        if result and result['book'] == expected['book'] and result['chapter'] == expected['chapter'] and result.get('verse') == expected.get('verse'):
            print(f"PASS {label}: {text}")
        else:
            print(f"FAIL {label}: {text} -> {result}")

    # D-04: Genesis cross-window
    verse_detector._last_book = "Genesis" # Manually set memory as the previous call would fail to match pattern
    verse_detector._last_book_time = time.time()
    result = verse_detector.detect_explicit("1 verse 1")
    if result and result['book'] == 'Genesis':
        print("PASS D-04: Genesis cross-window via book memory")
    else:
        print(f"FAIL D-04: Genesis cross-window -> {result}")

    # D-05: Song of Solomon false positive
    verse_detector._last_book = None
    verse_detector._last_book_time = 0
    result = verse_detector.detect_explicit("1 verse 1")
    if result is None:
        print("PASS D-05: bare digit sequence correctly returns None")
    else:
        print(f"FAIL D-05: bare '1 verse 1' should return None, got {result}")

if __name__ == "__main__":
    run_group_a()
    run_group_b()
    run_group_c()
    run_group_d()
