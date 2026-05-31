@echo off
setlocal
cd /d "%~dp0"
if /I "%~1"=="--self-test" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0panghu-codex-ui-installer.ps1" -SelfTest
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0panghu-codex-ui-installer.ps1"
)
endlocal
