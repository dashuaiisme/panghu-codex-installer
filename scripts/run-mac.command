#!/bin/zsh
cd "$(dirname "$0")/.."
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv || exit 1
fi

.venv/bin/python -c "import certifi, cryptography, webview" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  .venv/bin/python -m pip install --upgrade pip || exit 1
  .venv/bin/python -m pip install -r requirements-build.txt || exit 1
fi

.venv/bin/python src/panghu_codex_installer.py
