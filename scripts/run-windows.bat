@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -c "import certifi, cryptography, webview" >nul 2>nul
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1
    ".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" src\panghu_codex_installer.py
endlocal
