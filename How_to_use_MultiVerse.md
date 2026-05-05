✦ MultiVerse is a Python-based desktop application built with PyQt6 for the user interface, 
  utilizing the faster-whisper library for real-time transcription, and a local sqlite3     
  database for Bible verse lookups.

  How to use MultiVerse:

   1. Preparation:
       * Ensure you have Python 3.11+ installed.
       * Navigate to the project root directory in your terminal.
       * Activate the virtual environment: .\venv\Scripts\activate (or your platform        
         equivalent).

   2. Configuration:
       * Open config/config.ini and verify the [audio], [detection], and [display] sections 
         match your machine's setup (e.g., correct input_device_index for your microphone). 

   3. Launching the Application:  
       * Run the main entry point:
   1         python main.py       

   4. Operator Workflow:
       * Start Session: Once the application opens, click Session -> Start Session (or press         F5) to begin audio capture and real-time transcription.
       * Management: The Transcript Panel will display live text. Detected verses will      
         appear in the Approval Panel.
       * Display: In manual mode, review and click Approve to send the verse to the
         full-screen display window, or use Manual Lookup to search for specific verses.    
       * Session Utilities: Use File -> Export Session to save your transcript and history  
         to a text file.
       * Stop: Click Session -> Stop Session (or press F6) to halt processing.

  The project is now complete and fully committed. Please run /clear to finalize the        
  session.