import subprocess
import os

def run_test(cmd):
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ PASS\nOutput: {result.stdout.strip()[:100]}...")
            return True
        else:
            print(f"❌ FAIL\nError: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False

print("--- MultiVerse Final Verification ---")

tests = [
    "python verse_detector.py",
    "python -c \"from bible_db import get_verse; print(get_verse('John', 3, 16)['text'][:50])\"",
    "python -c \"from vector_search import search_paraphrase; print(search_paraphrase('no condemnation', 0.72))\"",
    "python -c \"from transcriber import transcribe_chunk; print('backend ok')\"",
    "python main.py --test-file tests/test_audio.wav"
]

results = []
for test in tests:
    results.append(run_test(test))

if all(results):
    print("\n🎉 ALL VERIFICATION GATES PASSED.")
else:
    print("\n🛑 SOME VERIFICATION GATES FAILED. Check the output above.")
