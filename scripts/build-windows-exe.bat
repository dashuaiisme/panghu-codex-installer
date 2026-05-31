@echo off
setlocal
cd /d "%~dp0.."
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name PanghuAI-Codex-Installer --distpath release --workpath build --specpath build src\panghu_codex_installer.py
echo Build finished.
echo release\PanghuAI-Codex-Installer\PanghuAI-Codex-Installer.exe
endlocal
