"""Enumerate Windows audio input devices for the Settings mic picker."""
from __future__ import annotations

import json
import logging
import subprocess
import sys

logger = logging.getLogger("windowverse.audio_devices")

FALLBACK = [{"id": "default", "name": "System Default Microphone", "is_default": True}]

# The MMDevices registry hive is the same list the Sound control panel shows:
# every capture endpoint, its friendly name, and its state (1 = active). It
# needs no extra modules and no WinRT projection, which is why the picker
# reads it instead of guessing from PnP friendly-name patterns.
_LIST_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$root = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture'
$nameKey = '{a45c254e-df1c-4efd-8020-67d146a850e0},2'
$descKey = '{b3f8fa53-0004-438e-9003-51a46e139bfc},6'
$defaultId = ''
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
  $defaultId = [Windows.Media.Devices.MediaDevice, Windows.Media.Devices, ContentType=WindowsRuntime]::GetDefaultAudioCaptureId(0)
} catch {}
$out = @()
foreach ($key in Get-ChildItem $root) {
  $props = Get-ItemProperty "$($key.PSPath)\Properties"
  if ($key.GetValue('DeviceState') -ne 1) { continue }
  $mic  = $props.$nameKey
  $dev  = $props.$descKey
  if (-not $mic -and -not $dev) { continue }
  $label = if ($mic -and $dev) { "$mic ($dev)" } elseif ($dev) { $dev } else { $mic }
  $guid = $key.PSChildName
  $out += [ordered]@{
    id = $guid
    name = $label
    is_default = [bool]($defaultId -and $defaultId.Contains($guid))
  }
}
if ($out.Count -eq 0) {
  $out += [ordered]@{ id = 'default'; name = 'System Default Microphone'; is_default = $true }
}
if (-not ($out | Where-Object { $_.is_default })) { $out[0].is_default = $true }
ConvertTo-Json -Compress -InputObject @($out)
"""


def list_input_devices() -> list[dict]:
    """Return [{id, name, is_default}, ...] for active capture endpoints."""
    if not sys.platform.startswith("win"):
        return list(FALLBACK)
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _LIST_SCRIPT],
            text=True, timeout=20, errors="replace",
        ).strip()
        if not out:
            return list(FALLBACK)
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        devices = [d for d in data if d.get("name")]
        return devices or list(FALLBACK)
    except Exception:
        logger.exception("Failed to enumerate audio devices")
        return list(FALLBACK)


def default_input_device() -> dict | None:
    """The endpoint WinRT will actually open, for display in Settings."""
    for dev in list_input_devices():
        if dev.get("is_default"):
            return dev
    return None


def set_default_input_device(device_name: str) -> bool:
    """Best-effort: set Windows default comms capture device by friendly name."""
    if not device_name or device_name.startswith("System Default"):
        return True
    if not sys.platform.startswith("win"):
        return False
    script = f"""
$ErrorActionPreference = 'SilentlyContinue'
Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
if (Get-Module AudioDeviceCmdlets) {{
  Set-AudioDevice -RecordingDeviceName "{device_name.replace('"', '`"')}" -ErrorAction SilentlyContinue
  exit 0
}}
exit 1
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except Exception:
        logger.warning("Could not set default mic to %r — WinRT will use OS default", device_name)
        return False
