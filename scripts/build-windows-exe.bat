@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows-exe.ps1"
exit /b %ERRORLEVEL%
