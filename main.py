# main.py

import sys
import os
# Force offline mode for all library calls
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
import logging
from configparser import ConfigParser, ExtendedInterpolation
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

from ui.main_window import MainWindow
from core.bible_db import BibleDB
from core.embedding_cache import EmbeddingLoader
from ui.styles import get_stylesheet
from utils.logger import setup_logger

def main():
    setup_logger(log_level="INFO")
    logger = logging.getLogger(__name__)

    config = ConfigParser(interpolation=ExtendedInterpolation())
    config.read('config/config.ini')

    app = QApplication(sys.argv)
    app.setStyleSheet(get_stylesheet())

    # 1. Initialize DB instantly
    bible_db = BibleDB(config.get('database', 'db_path'))
    
    # 2. Setup Background Embedding Loader
    loader_thread = QThread()
    loader = EmbeddingLoader(
        db_path=config.get('database', 'db_path'),
        model_cache=config.get('transcription', 'model_cache_path')
    )
    loader.moveToThread(loader_thread)

    # 3. Launch UI Immediately
    main_window = MainWindow(config, bible_db)
    main_window.show()
    main_window.start_worker()

    # 4. Connect Background Loader to UI
    loader.progress.connect(main_window.update_startup_progress)
    loader.ready.connect(main_window.on_models_ready)
    loader_thread.started.connect(loader.run)
    
    # Cleanup on quit
    def cleanup():
        loader_thread.quit()
        loader_thread.wait()

    app.aboutToQuit.connect(cleanup)
    
    # Start the "warm-up"
    loader_thread.start()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
