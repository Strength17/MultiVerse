# MultiVerse System Repository Report

## 1. System Overview
MultiVerse is a real-time scripture detection backend designed for offline, local execution on resource-constrained hardware (Intel N3530). It processes audio chunks, transcribes them using `faster-whisper` (or `openai-whisper` fallback), and performs dual-method detection:
- **Regex Detection:** For explicit scripture references.
- **Vector Search:** For paraphrased scripture references using FAISS/Sentence-Transformers.

## 2. Completed Enhancements
- **Transcript Buffer:** Replaced audio-overlap sliding window with a rolling text buffer (`deque`) to bridge cross-chunk verse references.
- **Regex Robustness:** Implemented "Book-First" validation and alias handling for common transcription errors (e.g., "was"/"worse" -> "verse").
- **Latency Optimization:** Pre-compiled regex patterns and added embedding model warm-up sequences to minimize initial trigger latency.
- **Cleanup:** Removed redundant files and legacy documentation to maintain repository hygiene.

## 3. Current Issues & Anomalies
- **False Positives:** The regex engine occasionally triggers false positives for "Song of Solomon 1:1" when encountering phrases like "1 was 1" because the regex pattern is still overly permissive with digit sequences.
- **CPU Bottleneck:** The N3530 CPU is the primary limitation. Transcription and vector embedding generation are compute-heavy, leading to high latency (15s–35s) for detected verses.
- **Transcript Sensitivity:** The detection accuracy is highly sensitive to transcription quality. Misheard book names or missing "chapter/verse" keywords cause trigger misses.

## 4. Top 3 Optimization Priorities
1.  **Strict Regex Contextualization (Accuracy):**
    - *Plan:* Modify regex to require a specific keyword (e.g., "chapter", "book of") to be present in the *same* or *immediately adjacent* chunks for digits to trigger a regex match. This will eliminate "1 was 1" type false positives.
2.  **Transcriber Model Distillation (Latency):**
    - *Plan:* Explore further quantization (int8) or distillation of the `tiny.en` model (if compatible) to reduce CPU load during inference.
3.  **Vector Search Index Optimization (Latency):**
    - *Plan:* Optimize FAISS `nprobe` settings to find the optimal balance between search speed and retrieval recall, ensuring vector detection stays under the 5-second target.

## 5. Inquiry for Future Development
Given the resource constraints (AVX-less CPU, low RAM), how can we best optimize the pipeline to achieve consistent sub-5s latency? Should we:
1.  Implement a lightweight "keyword-spotting" layer before Whisper transcription to only trigger transcription when "Bible/Scripture" keywords are heard?
2.  Shift to a completely different, smaller embedding model?
3.  Implement a multi-stage detection pipeline where regex is the primary trigger, and vector search is only invoked upon explicit request or failure?
