# core/vmix_bridge.py
import requests
import configparser
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class VMixBridge:
    """
    HTTP API wrapper for vMix integration.
    Handles communication with vMix's local API to display scripture overlays.
    """

    def __init__(self, config_path: str = 'config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        self.host = self.config.get('vmix', 'host', fallback='localhost')
        self.port = self.config.get('vmix', 'port', fallback='8088')
        self.base_url = f"http://{self.host}:{self.port}/api/"
        
        self.input_name = self.config.get('vmix', 'title_input_name', fallback='MultiVerse_Overlay')
        self.verse_text_el = self.config.get('vmix', 'verse_text_element', fallback='VerseBody.Text')
        self.ref_el = self.config.get('vmix', 'reference_element', fallback='VerseRef.Text')
        self.trans_el = self.config.get('vmix', 'translation_element', fallback='Translation.Text')

    def test_connection(self) -> Tuple[bool, str]:
        """
        Tests connection to vMix API.
        Returns (success: bool, message: str).
        """
        try:
            response = requests.get(f"{self.base_url}?Function=GetVersion", timeout=2)
            if response.status_code == 200:
                return True, "Connected to vMix"
            return False, f"vMix returned status {response.status_code}"
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to vMix: {e}")
            return False, str(e)

    def send_verse(self, text: str, reference: str, translation: str = 'KJV'):
        """
        Updates the vMix title input with verse details.
        
        Args:
            text: The scripture text to display.
            reference: The Bible book/chapter/verse reference.
            translation: The translation label to display.
        """
        params = [
            ('Function', 'SetText'),
            ('Input', self.input_name),
            ('SelectedName', self.verse_text_el),
            ('Value', text)
        ]
        
        try:
            requests.get(self.base_url, params=params, timeout=2)
            
            requests.get(self.base_url, params={
                'Function': 'SetText',
                'Input': self.input_name,
                'SelectedName': self.ref_el,
                'Value': reference
            }, timeout=2)
            
            requests.get(self.base_url, params={
                'Function': 'SetText',
                'Input': self.input_name,
                'SelectedName': self.trans_el,
                'Value': translation
            }, timeout=2)
            
            # Fade in the overlay
            requests.get(self.base_url, params={
                'Function': 'OverlayInput1',
                'Input': self.input_name
            }, timeout=2)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update vMix overlay: {e}")

    def clear_overlay(self):
        """
        Clears the vMix overlay.
        """
        try:
            requests.get(self.base_url, params={'Function': 'OverlayInput1Out'}, timeout=2)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to clear vMix overlay: {e}")
