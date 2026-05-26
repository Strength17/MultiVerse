# Manual Testing Instructions for MultiVerse

The MultiVerse backend is fully operational and ready for real-time manual testing directly from your terminal.

## How to Test

1. **Navigate to the Project Directory:**
   ```powershell
   cd C:\Users\Strenght Awa\Desktop\PERSONAL\multiverse-gemini
   ```

2. **Launch the Live Backend:**
   ```powershell
   python main.py
   ```

## What to Expect

*   **Initialization:** The system will load the Whisper model (this may take a few seconds).
*   **Listening:** You will see the prompt: `Live mic started. Speak now...`
*   **Real-Time Feedback:**
    *   **Transcripts:** Every 3 seconds, the system will log the transcript of what it heard to your terminal (`[INFO] Transcript: '...'`).
    *   **Detection:** If a scripture is detected, it will output a JSON payload, for example:
        `{"triggered": true, "source": "regex", "book": "Romans", "chapter": 8, "verse": 1, ...}`
    *   If no scripture is detected, it will output: `{"triggered": false}`.

## Test Phrases
Speak these phrases clearly with a 2-second pause between them:
- "Romans chapter 8 verse 1"
- "Those who worship God must worship in spirit and in truth"
- "Genesis chapter 1 verse 1"
- "God created man in His image and in His likeness"

## Graceful Shutdown
To stop the system, press **`Ctrl+C`**. The backend will print a session summary and shut down cleanly.

*Note: Given the N3530 hardware constraints, please speak slowly. If you see "Queue full" warnings, pause for a moment to allow the system to catch up.*
