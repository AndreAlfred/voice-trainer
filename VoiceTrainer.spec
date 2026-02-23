# VoiceTrainer.spec — PyInstaller build specification for macOS .app bundle.
#
# Build with: pyinstaller VoiceTrainer.spec
# Or use:     ./build_app.sh   (handles venv activation + signing automatically)

import os
import sounddevice

# Path to sounddevice's bundled PortAudio binary.
# sounddevice ships its own PortAudio .dylib inside _sounddevice_data/.
# PyInstaller won't find it automatically — we declare it explicitly.
# Note: _sounddevice_data is a sibling of sounddevice inside site-packages,
# so we use the same directory as sounddevice.__file__ (not one level up).
_sd_data_src = os.path.join(os.path.dirname(sounddevice.__file__), '_sounddevice_data')
_sd_data_src = os.path.normpath(_sd_data_src)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (_sd_data_src, '_sounddevice_data'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtOpenGL',
        'pyqtgraph',
        'numpy',
        'scipy',
        'scipy.signal',
        'sounddevice',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zlib, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceTrainer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,       # UPX compression can break PySide6 binaries — leave off
    console=False,   # no terminal window when launched from Finder
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceTrainer',
)

app = BUNDLE(
    coll,
    name='VoiceTrainer.app',
    icon=None,
    bundle_identifier='com.voicetrainer.app',
    info_plist={
        # Required for microphone access — without this macOS gives the app no audio
        'NSMicrophoneUsageDescription': (
            'Voice Trainer needs microphone access to analyze your singing voice in real time.'
        ),
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'CFBundleName': 'Voice Trainer',
        'CFBundleDisplayName': 'Voice Trainer',
    },
)
