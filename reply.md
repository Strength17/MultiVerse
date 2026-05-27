# Optimization and Cleanup Plan

## 1. Unnecessary Files for Cleanup
The following files are redundant and should be removed to reduce clutter and maintain repository integrity:
- `golden_run/`: Old reference implementation/backup directory.
- `report.md`, `repo_report.md`: Historical logs/reports that are no longer accurate or necessary.
- `final_verify.py`: Redundant verification script; project verification is now covered by `TRANSCRIPT_BUFFER_WORKFLOW.md`.
- `download_tiny.py`: We use `local_files_only=True` for offline robustness; this script is no longer used.
- `vs_BuildTools.exe`: Large binary file likely present by mistake; not needed for project operation.
- `inspect_db.py`: Simple utility that can be replaced by a one-liner if needed in the future.

## 2. Detection Logic Improvement (Regex & Robustness)
To fix issues where "was" is misheard for "verse", and to improve robustness against spelling errors and variations:
- **Regex Expansion:** Update `verse_detector.py` to use fuzzy regex or expand the keyword list. Specifically, add common mishearings (e.g., "was", "worse") as aliases for "verse" in a localized context near book/chapter matches.
- **Contextual Awareness:** Modify the detection logic to be "attentive" when a book name is identified. If a book name is detected, the regex window should tighten and prioritize looking for chapter/verse keywords (including aliases) in the immediate tokens following.
- **Expected Improvement:** +15-20% in verse detection accuracy.

## 3. Latency Optimization Plan
To achieve <1s regex and <5s vector detection:
- **Regex Optimization:** Compile regex patterns at the module level in `verse_detector.py` to minimize per-call overhead.
- **Vector Search Optimization:**
    - **Index Memory Mapping:** Ensure the FAISS index is loaded into memory at startup (already done, but can be optimized by using `faiss.read_index_binary` or `mmap`).
    - **Inference Warm-up:** Add a "warm-up" step in `main.py` that processes a dummy string through the embedding model during startup. This avoids the model being lazy-loaded on the first detection, which is currently the main source of the latency spike (e.g., ~19s for some triggers).
- **Concurrency:** Ensure detection happens in the transcription thread but offload DB lookups to be non-blocking if possible.

## 4. Expected Performance Targets
| Metric | Current Baseline (Warm) | Target |
| :--- | :--- | :--- |
| **Regex Detection** | ~1-2s (spike-dependent) | < 0.5s |
| **Vector Detection** | ~4-6s (spike-dependent) | < 3s |

*These optimizations are designed to leverage existing local resources without needing external software/downloads.*
