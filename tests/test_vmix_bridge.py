# tests/test_vmix_bridge.py
import pytest
from unittest.mock import patch, MagicMock
from core.vmix_bridge import VMixBridge
import requests

@pytest.fixture
def bridge():
    return VMixBridge()

def test_test_connection_success(bridge):
    """Verify test_connection returns True when vMix is reachable."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        success, message = bridge.test_connection()
        assert success is True
        assert "Connected" in message

def test_test_connection_failure(bridge):
    """Verify test_connection returns False when vMix is unreachable."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        success, message = bridge.test_connection()
        assert success is False
        assert "Connection refused" in message

def test_send_verse(bridge):
    """Verify send_verse makes the expected HTTP calls."""
    with patch('requests.get') as mock_get:
        bridge.send_verse("In the beginning", "Genesis 1:1", "KJV")
        
        # Should call SetText 3 times and OverlayInput1 1 time
        assert mock_get.call_count == 4
        
        # Verify first call (verse text)
        args, kwargs = mock_get.call_args_list[0]
        params = kwargs.get('params')
        # params can be a list of tuples or a dict depending on implementation
        # In core/vmix_bridge.py it is a list of tuples for the first call
        params_dict = dict(params)
        assert params_dict['Function'] == 'SetText'
        assert params_dict['Value'] == "In the beginning"

def test_clear_overlay(bridge):
    """Verify clear_overlay makes the expected HTTP call."""
    with patch('requests.get') as mock_get:
        bridge.clear_overlay()
        assert mock_get.call_count == 1
        args, kwargs = mock_get.call_args
        params = kwargs.get('params')
        assert params['Function'] == 'OverlayInput1Out'
