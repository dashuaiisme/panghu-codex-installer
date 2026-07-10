@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================================
echo   胖虎AI客户端 - 本机环境校验 (Windows)
echo   直接读取真实文件, 不经过 Cowork 沙箱, 结果可信
echo ================================================================
echo.

REM --- 1. 检查 Python ---
where python >nul 2>&1
if errorlevel 1 (
  echo [X] 没找到 python 命令。请先安装 Python 3.10+ 并勾选 "Add to PATH"。
  echo     下载: https://www.python.org/downloads/
  goto :end
)
for /f "delims=" %%v in ('python --version 2^>^&1') do echo [OK] 检测到 %%v

REM --- 2. 虚拟环境 (没有就创建) ---
if not exist ".venv\Scripts\python.exe" (
  echo [..] 未发现虚拟环境, 正在创建 .venv ...
  python -m venv .venv
  if errorlevel 1 ( echo [X] 创建虚拟环境失败。 & goto :end )
)
call ".venv\Scripts\activate.bat"
echo [OK] 已激活虚拟环境 .venv

REM --- 3. 安装依赖 ---
echo.
echo [..] 安装/更新依赖 (requirements-build.txt) ...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements-build.txt
if errorlevel 1 ( echo [X] 依赖安装失败, 请检查网络。 & goto :end )
echo [OK] 依赖就绪

REM --- 4. 语法校验: 编译所有源码 (真正的语法检查, 不受沙箱截断影响) ---
echo.
echo ================= 语法校验 (src + scripts + tests) =================
python -m compileall -q src scripts tests
if errorlevel 1 (
  echo.
  echo [X] 发现真实语法错误, 见上方。这才是需要修的地方。
  goto :end
)
echo [OK] 所有 .py 文件语法正确 —— 没有任何真实的语法/截断问题
echo      ^(如果 Cowork 沙箱报某个文件语法错, 那是沙箱读取截断的假象, 忽略即可^)

REM --- 5. 运行测试 ---
echo.
echo ======================= 运行测试 (pytest) =======================
python -m pytest -q
if errorlevel 1 (
  echo.
  echo [!] 有测试未通过, 见上方输出。
  goto :end
)
echo.
echo [OK] 全部通过 —— 环境正常, 代码可信。

:end
echo.
echo ================================================================
pause
endlocal
