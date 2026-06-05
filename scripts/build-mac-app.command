#!/bin/zsh
cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed --name "胖虎AI-Codex一键安装工具" --distpath release --workpath build --specpath build src/panghu_codex_installer.py
echo "Build finished. App is under release/"
