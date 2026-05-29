# Results: Higher Vector Threshold (0.72)

### 1. Performance Overview
The system was tested with `vector_threshold = 0.72` on the `feature/transcript-buffer-test` branch.

### 2. Detection Results
- **Verses Triggered:** 2 (John 4:24, Genesis 1:27)
- **Verses Missed:** 2 (Romans 8:1, Genesis 1:1)

| Verse | Triggered | Confidence Score |
| :--- | :--- | :--- |
| **Romans 8:1** | **Missed** | N/A |
| **John 4:24** | **Triggered** | 0.76 |
| **Genesis 1:1** | **Missed** | N/A |
| **Genesis 1:26** | **Triggered** | 0.75 |

### 3. Analysis
Increasing the `vector_threshold` to 0.72 made the detection significantly more restrictive. While John 4:24 and Genesis 1:27 (as verse 27) were successfully triggered, Romans 8:1 and Genesis 1:1 were missed.

For the system to reliably catch all four main target verses, the current vector threshold appears to be too high, filtering out valid paraphrases that have confidence scores below 0.72. The previous threshold of 0.65 or a slightly adjusted one (e.g., 0.70) is more likely to maintain a balance between precision and recall.
