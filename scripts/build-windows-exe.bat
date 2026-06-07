@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name PanghuAI-Agent-Deployer --icon "%CD%\assets\panghu.ico" --add-data "%CD%\assets;assets" --distpath release --workpath build --specpath build src\panghu_codex_installer.py
if exist "release\PanghuAI-Agent-Deployer-Windows.zip" del /f /q "release\PanghuAI-Agent-Deployer-Windows.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath 'release\PanghuAI-Agent-Deployer' -DestinationPath 'release\PanghuAI-Agent-Deployer-Windows.zip' -Force"
echo Build finished.
echo release\PanghuAI-Agent-Deployer\PanghuAI-Agent-Deployer.exe
echo release\PanghuAI-Agent-Deployer-Windows.zip
endlocal
