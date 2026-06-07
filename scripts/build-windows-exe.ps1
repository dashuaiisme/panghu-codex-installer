$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
if (-not (Test-Path -LiteralPath ".venv")) {
    python -m venv .venv
}
$python = Join-Path $root ".venv\Scripts\python.exe"
$assets = Join-Path $root "assets"
$icon = Join-Path $assets "panghu.ico"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-build.txt
& $python -m PyInstaller --noconfirm --clean --windowed --name "PanghuAI-Agent-Deployer" --icon $icon --add-data "${assets};assets" --distpath release --workpath build --specpath build src\panghu_codex_installer.py
$zip = Join-Path $root "release\PanghuAI-Agent-Deployer-Windows.zip"
if (Test-Path -LiteralPath $zip) {
    Remove-Item -LiteralPath $zip -Force
}
Compress-Archive -LiteralPath (Join-Path $root "release\PanghuAI-Agent-Deployer") -DestinationPath $zip -Force
Write-Host "Build finished."
Write-Host "release\PanghuAI-Agent-Deployer\PanghuAI-Agent-Deployer.exe"
Write-Host "release\PanghuAI-Agent-Deployer-Windows.zip"
