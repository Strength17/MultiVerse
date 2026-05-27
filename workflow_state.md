# Workflow State

## Phase 0: Cleanup
- [x] Delete redundant files (`golden_run`, `report.md`, `repo_report.md`, `final_verify.py`, `download_tiny.py`, `vs_BuildTools.exe`, `inspect_db.py`)

## Phase 1: Regex & Robustness Improvement
- [ ] Update `verse_detector.py` with expanded alias support for "verse"
- [ ] Implement book-name-attentive regex tightening
- [ ] Verification Test & Performance Lock

## Phase 2: Latency Optimization
- [ ] Implement FAISS index memory mapping/loading optimizations
- [ ] Add embedding model warm-up in `main.py`
- [ ] Verification Test & Performance Lock

## Phase 3: Final Verification
- [ ] Run full system verify gate
- [ ] Final performance lock
