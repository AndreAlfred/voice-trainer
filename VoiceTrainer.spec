# VoiceTrainer.spec — PyInstaller build specification for macOS .app bundle.
#
# Build with: pyinstaller VoiceTrainer.spec
# Or use:     ./build_app.sh   (handles venv activation + signing automatically)

import os
import importlib.util

# Locate sounddevice's bundled PortAudio binary.
# sounddevice ships its own PortAudio .dylib inside _sounddevice_data/.
# PyInstaller won't find it automatically — we declare it explicitly.
_sd_spec = importlib.util.find_spec('sounddevice')
if _sd_spec is None:
    raise SystemExit(
        "ERROR: sounddevice not found. Run PyInstaller from the project venv:\n"
        "  source venv/bin/activate\n"
        "  pyinstaller VoiceTrainer.spec\n"
        "Or use: ./build_app.sh"
    )
_sd_data_src = os.path.join(os.path.dirname(_sd_spec.origin), '_sounddevice_data')

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
        'PySide6.QtOpenGLWidgets',
        'pyqtgraph',
        'numpy',
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
