#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-build.txt
APP_NAME="胖虎AI多Agent一键部署工具"
ROOT="$(pwd)"
ASSETS="$ROOT/assets"
.venv/bin/python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ASSETS/panghu-avatar.icns" \
  --add-data="$ASSETS:assets" \
  --distpath release \
  --workpath build \
  --specpath build \
  src/panghu_codex_installer.py
APP_PATH="release/${APP_NAME}.app"
ZIP_PATH="release/${APP_NAME}-Mac.zip"
if [ -d "$APP_PATH" ]; then
  /usr/bin/codesign --force --deep --sign - "$APP_PATH" >/dev/null 2>&1 || true
fi
rm -f "$ZIP_PATH"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
echo "Build finished."
echo "$APP_PATH"
echo "$ZIP_PATH"
