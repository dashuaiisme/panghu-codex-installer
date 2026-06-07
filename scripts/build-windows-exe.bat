@echo off
setlocal
cd /d "%~dp0.."
set APP_NAME=胖虎AI多Agent一键部署工具
if not exist .venv python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name "%APP_NAME%" --icon "%CD%\assets\panghu-avatar.ico" --add-data "%CD%\assets;assets" --distpath release --workpath build --specpath build src\panghu_codex_installer.py
if exist "release\%APP_NAME%-Windows.zip" del /f /q "release\%APP_NAME%-Windows.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath 'release\%APP_NAME%' -DestinationPath 'release\%APP_NAME%-Windows.zip' -Force"
echo Build finished.
echo release\%APP_NAME%\%APP_NAME%.exe
echo release\%APP_NAME%-Windows.zip
endlocal
