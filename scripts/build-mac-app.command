#!/bin/zsh
cd "$(dirname "$0")/.."
python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller --noconfirm --clean --windowed --name "胖虎AI-Codex一键安装工具" --distpath release --workpath build --specpath build src/panghu_codex_installer.py
echo "Build finished. App is under release/"
