# main.py

import sys
import os
import logging
from configparser import ConfigParser, ExtendedInterpolation
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

# Project imports
from ui.main_window import MainWindow
from ui.scripture_display import ScriptureDisplay
from core.bible_db import BibleDB
from core.transcription_worker import TranscriptionWorker
from utils.logger import setup_logger

def main():
    # Setup logging
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    setup_logger(log_level="DEBUG")
    logger = logging.getLogger(__name__)
    logger.info("MultiVerse starting...")

    # Load configuration
    config = ConfigParser(interpolation=ExtendedInterpolation())
    config.read('config.ini')
    # Attach path for SettingsDialog in MainWindow
    config.path = 'config.ini'

    app = QApplication(sys.argv)
    app.setApplicationName("MultiVerse")

    # Initialize Bible Database
    bible_db = BibleDB()

    # Create Scripture Display Window (Stand-alone output)
    display_window = ScriptureDisplay()
    
    # Create Main Operator Window
    main_window = MainWindow(config, display_window, bible_db)

    # Setup Transcription Worker and Thread
    worker_thread = QThread()
    worker = TranscriptionWorker(config, bible_db)
    worker.moveToThread(worker_thread)

    # Connections for Worker
    # Started/Stopped via MainWindow signals
    main_window.session_started.connect(lambda: worker_thread.start() if not worker_thread.isRunning() else worker.start_processing())
    main_window.session_stopped.connect(worker.stop_processing)
    
    worker_thread.started.connect(worker.start_processing)
    worker.transcript_signal.connect(main_window.transcript_panel.append_transcript)
    worker.verse_detected_signal.connect(main_window.approval_panel.update_proposal)
    worker.status_signal.connect(lambda msg: main_window.statusBar().showMessage(msg, 5000))
    worker.error_signal.connect(lambda msg: main_window.statusBar().showMessage(f"Error: {msg}", 0))

    # Wiring MainWindow signals to Display and Worker
    # (Many connections already happen inside MainWindow.__init__)
    
    # Handle application shutdown
    def cleanup():
        logger.info("Shutting down...")
        try:
            worker.stop_processing()
            if worker_thread.isRunning():
                worker_thread.quit()
                worker_thread.wait(2000) # Wait up to 2 seconds
            display_window.close()
            bible_db.close()
            logger.info("Cleanup complete.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    app.aboutToQuit.connect(cleanup)

    # Show windows
    main_window.show()
    
    # Optionally show display window based on config or user action
    # For MVP, we show it automatically
    display_window.show()

    # Worker thread NOT started automatically. Operator clicks "Start Session".

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
