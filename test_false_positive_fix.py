from verse_detector import detect_explicit

# Test 1: The previous False Positive should now be None
text = "Now let's open up the Bible to the book of chapter 1"
result = detect_explicit(text)
print(f"Result for '{text}': {result}")
assert result is None, f"FAIL: False positive detected for '{text}': {result}"
print("PASS: False positive eliminated")

# Test 2: Actual scripture should still trigger
text2 = "Song of Solomon chapter 1 verse 1"
result2 = detect_explicit(text2)
print(f"Result for '{text2}': {result2}")
assert result2 is not None, "FAIL: Actual scripture not detected"
assert result2['book'] == "Song of Solomon"
print("PASS: Actual scripture detected")
