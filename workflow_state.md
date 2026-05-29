# Workflow State: Refinement Plan

## Phase 1: Robust Regex & False Positive Elimination
- [ ] **Task 1-A:** Modify `verse_detector.py` to require stronger keyword presence for digits not explicitly identified as chapters.
- [ ] **Task 1-B:** Implement "Book-First" validation: only trigger detection if the identified word matches a book name with >85% fuzzy confidence.
- [ ] **Task 1-C:** Test run against `tests/test_audio.wav`. Success criteria: No false positives (Song of Solomon), all 4 target verses triggered.

## Phase 2: Latency Optimization
- [ ] **Task 2-A:** Profile `detect_explicit` for overhead; implement pre-compiled regex caching.
- [ ] **Task 2-B:** Optimize FAISS index search by enabling `mmap` if possible or using `index.nprobe` settings.
- [ ] **Task 2-C:** Test run with full timing logs. Success criteria: Regex < 0.5s, Vector < 3s.

## Phase 3: Final Verification
- [ ] **Task 3-A:** Execute 3 consecutive performance tests.
- [ ] **Task 3-B:** Log results in a table (transcription time, identification time, verse found) in `analysis.md`.
- [ ] **Task 3-C:** Final commit and report generation in `reply.md`.
