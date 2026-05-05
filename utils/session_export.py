# utils/session_export.py

import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def export_session_log(transcript_text: str, history_entries: list, export_path: str) -> bool:
    """
    Exports the session transcript and verse history to a text file.

    Args:
        transcript_text (str): The full accumulated transcript text.
        history_entries (list): A list of strings representing the verse history log.
        export_path (str): The file path to save the export.

    Returns:
        bool: True if export was successful, False otherwise.
    """
    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("MultiVerse Session Export\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*30 + "\n\n")

            f.write("VERSE HISTORY LOG:\n")
            f.write("-" * 20 + "\n")
            if history_entries:
                for entry in history_entries:
                    f.write(f"{entry}\n")
            else:
                f.write("(No verses sent this session)\n")
            
            f.write("\n\nFULL TRANSCRIPT:\n")
            f.write("-" * 20 + "\n")
            if transcript_text.strip():
                f.write(transcript_text)
            else:
                f.write("(Transcript was empty)")
            
            f.write("\n\n" + "="*30 + "\n")
            f.write("End of Export\n")
            
        logger.info(f"Session exported successfully to {export_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export session: {e}")
        return False
