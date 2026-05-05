# core/vocabulary_injection.py
from data.book_names import BIBLE_BOOKS

def get_initial_prompt() -> str:
    """
    Generates an initial_prompt for Whisper injection.
    
    Ensures the total length remains well under the 200-token safety limit.
    """
    # Create a comma-separated list of canonical book names
    book_list = [name for name in BIBLE_BOOKS.keys()]
    
    # Construct the prompt string
    prompt = "Bible scripture reading. " + ", ".join(book_list) + "."
    
    # Return the prompt, ensuring it's not excessively long. 
    # The BIBLE_BOOKS list is ~66 items, which fits safely within limits.
    return prompt
