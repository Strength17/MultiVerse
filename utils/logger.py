# utils/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(log_level: str = "INFO") -> None:
    """
    Initialises the project-wide logging configuration with rotation and console output.
    
    Args:
        log_level (str): The logging level as a string (e.g., "DEBUG", "INFO", "WARNING").
                         Defaults to "INFO".
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "multiverse.log"
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Define the log format
    # Structured as: Timestamp - Module Name - Level - Message
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Rotating File Handler: 10MB per file, keeping 5 old logs
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10 * 1024 * 1024, 
        backupCount=5, 
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    
    # Console Handler for real-time feedback in terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers to prevent duplicate logs if setup_logger is called multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    # Add the handlers to the root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Prevent third-party libraries (like faster-whisper) from flooding the log unless DEBUG
    if numeric_level > logging.DEBUG:
        logging.getLogger("faster-whisper").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info("Logging initialised. Level: %s, File: %s", log_level.upper(), log_file)
