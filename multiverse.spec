# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for MultiVerse desktop app."""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'ui'), 'ui'),
        (str(ROOT / 'config'), 'config'),
        (str(ROOT / 'data' / 'README_DATA.txt'), 'data'),
        (str(ROOT / 'data' / 'backgrounds' / 'README.txt'), 'data/backgrounds'),
        (str(ROOT / 'assets' / 'multiverse.ico'), 'assets'),
        (str(ROOT / 'assets' / 'multiverse_logo.png'), 'assets'),
        (str(ROOT / 'NDI_SETUP.md'), '.'),
        (str(ROOT / 'COMMANDS.md'), '.'),
    ],
    hiddenimports=[
        'websockets', 'websockets.legacy', 'websockets.legacy.server',
        'winrt', 'winrt.runtime', 'winrt._winrt',
        'winrt.windows.foundation', 'winrt.windows.foundation.collections',
        'winrt.windows.media.speechrecognition',
        'winrt.windows.storage', 'winrt.windows.globalization',
        'faiss', 'sentence_transformers', 'rapidfuzz', 'word2number',
        'pythonosc', 'cyndilib', 'PIL', 'numpy', 'tqdm',
        'torch', 'transformers', 'sklearn', 'scipy',
        'static_server', 'paths', 'verse_display', 'audio_devices',
        'server', 'detection_orchestrator', 'verse_detector', 'vector_search',
        'bible_library', 'bible_db', 'winrt_pipeline', 'ndi_sender',
        'app_config', 'console_output', 'vocab_correction',
        'error_catalog', 'detection_filters', 'reference_context',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MultiVerse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'multiverse.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MultiVerse',
)
