$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name "PanghuAI-Codex-Installer" --distpath release --workpath build --specpath build src\panghu_codex_installer.py
Write-Host "Build finished."
Write-Host "release\PanghuAI-Codex-Installer\PanghuAI-Codex-Installer.exe"
