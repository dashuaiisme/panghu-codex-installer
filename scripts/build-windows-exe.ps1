$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
if (-not (Test-Path -LiteralPath ".venv")) {
    python -m venv .venv
}
$python = Join-Path $root ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-build.txt
& $python -m PyInstaller --noconfirm --clean --windowed --name "PanghuAI-Agent-Deployer" --distpath release --workpath build --specpath build src\panghu_codex_installer.py
Write-Host "Build finished."
Write-Host "release\PanghuAI-Agent-Deployer\PanghuAI-Agent-Deployer.exe"
