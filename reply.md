# Detailed Implementation Plan

## Overview
This plan aims to stabilize verse detection, eliminate false positives, and reduce detection latency to meet target performance benchmarks.

## Phase 1: Robust Regex & False Positive Elimination
**Objective:** Eliminate the "Song of Solomon 1:1" false positive and tighten book-name matching.
**Strategy:** 
1.  **Strict Regex:** Disallow the `r'(.+?)\s+(\d+)\s+(\d+)'` pattern (the culprit) unless it is explicitly preceded by "chapter" or "verse" keywords.
2.  **Book-First Validation:** Update `detect_explicit` to first perform a fuzzy book match against `BOOK_NAME_TO_NUMBER`. Only proceed with regex pattern matching if the book name confidence score >= 85%.

## Phase 2: Latency Optimization
**Objective:** Target < 0.5s for regex, < 3s for vector detection.
**Strategy:**
1.  **Regex Caching:** Move `re.compile` patterns to global scope (module load time) to eliminate redundant compilation.
2.  **Vector Search:** Maintain embedding model warm-up (already implemented) and investigate `faiss` index parameters (`nprobe`) for efficiency versus accuracy trade-offs.

## Phase 3: Final Verification
**Objective:** Verify performance and track metrics.
**Measurement:** 3-test average for latency, trigger count for accuracy.

---

### Expected Performance Improvement
- **Accuracy:** 100% (4/4 targeted verses), 0% false positives.
- **Latency:** ~30-50% reduction in total detection cycle time.
