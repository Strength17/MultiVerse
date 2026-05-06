# main.py

import sys
import os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
import logging
from configparser import ConfigParser, ExtendedInterpolation
from PyQt6.QtWidgets import QApplication, QProgressBar, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QThread, Qt

from ui.main_window import MainWindow
from ui.scripture_display import ScriptureDisplay
from core.bible_db import BibleDB
from core.embedding_cache import EmbeddingLoader
from ui.styles import get_stylesheet
from utils.logger import setup_logger

def main():
    setup_logger(log_level="INFO")
    logger = logging.getLogger(__name__)

    config = ConfigParser(interpolation=ExtendedInterpolation())
    files_read = config.read('config/config.ini')
    print(f"DEBUG: CWD={os.getcwd()}, Files read={files_read}, Sections={config.sections()}")

    app = QApplication(sys.argv)
    app.setStyleSheet(get_stylesheet())

    # Splash screen for embedding load
    splash = QWidget()
    splash.setWindowTitle("MultiVerse — Loading...")
    splash.setFixedSize(400, 150)
    layout = QVBoxLayout(splash)
    layout.addWidget(QLabel("Pre-computing verse embeddings..."))
    progress = QProgressBar()
    layout.addWidget(progress)
    splash.show()

    # Embedding Loader Thread
    loader_thread = QThread()
    # Pass section-specific config values
    loader = EmbeddingLoader(
        db_path=config.get('database', 'db_path'),
        model_cache=config.get('transcription', 'model_cache_path')
    )
    loader.moveToThread(loader_thread)
    
    bible_db = BibleDB(config.get('database', 'db_path'))
    
    def on_ready(model, matrix, refs):
        display_window = ScriptureDisplay(config)
        main_window = MainWindow(config, bible_db)
        
        main_window.show()
        splash.close()
        loader_thread.quit()

    loader.progress.connect(progress.setValue)
    loader.ready.connect(on_ready)
    loader_thread.started.connect(loader.run)
    loader_thread.start()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
