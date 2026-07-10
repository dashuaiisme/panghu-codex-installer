@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动本地界面预览，请勿关闭本窗口...
echo 浏览器会自动打开；若没打开，手动访问：
echo    http://localhost:8765/src/ui/index.html?preview=agent
python "%~dp0_preview_server.py"
pause
