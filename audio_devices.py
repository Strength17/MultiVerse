"""Enumerate Windows audio input devices for the Settings mic picker."""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger("multiverse.audio_devices")


def list_input_devices() -> list[dict]:
    """Return [{id, name, is_default}, ...] using PowerShell + MMDevice API."""
    ps = r"""
Add-Type @"
using System.Runtime.InteropServices;
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator { int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out object ppDevice); }
"@ 2>$null
$devices = @()
try {
  $code = @'
import subprocess, json, re
out = subprocess.check_output([
  "powershell","-NoProfile","-Command",
  "Get-CimInstance Win32_SoundDevice | Where-Object {$_.Status -eq 'OK'} | Select-Object -ExpandProperty Name"
], text=True, errors='ignore')
names = [n.strip() for n in out.splitlines() if n.strip()]
print(json.dumps([{"id": str(i), "name": n, "is_default": i==0} for i,n in enumerate(names)]))
'@
} catch {}
"""
    try:
        script = """
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$devEnum = [Windows.Media.Devices.MediaDevice]::GetDefaultAudioCaptureId([Windows.Media.Capture.MediaCategory]::Communications)
$all = [System.Collections.Generic.List[object]]::new()
$i = 0
try {
  $sessions = Get-PnpDevice -Class AudioEndpoint -Status OK | Where-Object { $_.FriendlyName -match 'Microphone|Headset|Array|Input|Mic' }
  foreach ($d in $sessions) {
    $name = $d.FriendlyName
    if ($name) {
      $all.Add([ordered]@{ id = [string]$i; name = $name; is_default = ($i -eq 0) })
      $i++
    }
  }
} catch {}
if ($all.Count -eq 0) {
  $all.Add([ordered]@{ id = 'default'; name = 'System Default Microphone'; is_default = $true })
}
$all | ConvertTo-Json -Compress
"""
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True, timeout=15, errors="replace",
        ).strip()
        if not out:
            return [{"id": "default", "name": "System Default Microphone", "is_default": True}]
        import json
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        logger.exception("Failed to enumerate audio devices")
        return [{"id": "default", "name": "System Default Microphone", "is_default": True}]


def set_default_input_device(device_name: str) -> bool:
    """Best-effort: set Windows default comms capture device by friendly name."""
    if not device_name or device_name.startswith("System Default"):
        return True
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
