@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name PanghuAI-Agent-Deployer --distpath release --workpath build --specpath build src\panghu_codex_installer.py
echo Build finished.
echo release\PanghuAI-Agent-Deployer\PanghuAI-Agent-Deployer.exe
endlocal
