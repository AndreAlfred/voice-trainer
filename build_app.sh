#!/bin/bash
# build_app.sh — Build VoiceTrainer.app for macOS.
#
# Usage:
#   ./build_app.sh
#
# Output: dist/VoiceTrainer.app  (drag to /Applications to install)
#
# Requirements:
#   - Run from the voice-trainer project root
#   - venv must already be set up (python3 -m venv venv && pip install -r requirements.txt)

set -e  # stop immediately on any error

echo "==> Activating virtual environment..."
source venv/bin/activate

echo "==> Installing PyInstaller (if not already installed)..."
pip install pyinstaller --quiet

echo "==> Cleaning previous build artifacts..."
rm -rf build dist

echo "==> Building VoiceTrainer.app with PyInstaller..."
pyinstaller VoiceTrainer.spec

echo "==> Applying ad-hoc code signature..."
# Ad-hoc signing (uses '-' as identity = local self-signed).
# This prevents the Gatekeeper warning when launching on THIS Mac.
# To distribute, replace '-' with your Apple Developer certificate name.
codesign --deep --force --sign - dist/VoiceTrainer.app

echo ""
echo "Build complete."
echo ""
echo "  App:     dist/VoiceTrainer.app"
echo "  Install: drag dist/VoiceTrainer.app to /Applications"
echo ""
