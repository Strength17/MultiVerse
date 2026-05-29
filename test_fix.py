import sys
sys.path.insert(0, '.')
from verse_detector import detect_explicit

# Test A — the split chunk fix
combined = "romans chapter 8 verse 1"
result = detect_explicit(combined)
assert result is not None, "FAIL: Romans 8:1 not detected from clean combined text"
assert result['book'].lower() == 'romans', f"FAIL: wrong book {result['book']}"
assert result['chapter'] == 8, f"FAIL: wrong chapter {result['chapter']}"
assert result['verse'] == 1, f"FAIL: wrong verse {result['verse']}"
print("PASS: Romans 8:1 detected from combined buffer text")

split_combined = "romans chapter 8  verse 1"
result2 = detect_explicit(split_combined)
assert result2 is not None, "FAIL: Romans 8:1 not detected from split-chunk normalized text"
print("PASS: Romans 8:1 detected from split-chunk normalized text")

# Test B — false positive eliminated
false_positive_text = "chapter 1 was 1 you know where we talk about creation"
result = detect_explicit(false_positive_text)
if result is None:
    print("PASS: 'chapter 1 was 1' correctly returns None (no false positive)")
else:
    print(f"FAIL: triggered {result} — should be None")
    sys.exit(1)

# Test C — genuine explicit reference still works
cases = [
    ("john chapter 3 verse 16", "john", 3, 16),
    ("genesis chapter 1 verse 1", "genesis", 1, 1),
    ("romans chapter 8 verse 1", "romans", 8, 1),
    ("psalms 121 1", "psalms", 121, 1),
]
for text, book, ch, v in cases:
    r = detect_explicit(text)
    assert r is not None, f"FAIL: '{text}' returned None"
    assert r['book'].lower() == book, f"FAIL: {text} → wrong book {r['book']}"
    assert r['chapter'] == ch, f"FAIL: {text} → wrong chapter {r['chapter']}"
    assert r['verse'] == v, f"FAIL: {text} → wrong verse {r['verse']}"
    print(f"PASS: {text}")
print("All regression tests passed")
