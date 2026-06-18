$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
if (-not (Test-Path -LiteralPath ".venv")) {
    python -m venv .venv
}
$python = Join-Path $root ".venv\Scripts\python.exe"
$assets = Join-Path $root "assets"
$icon = Join-Path $assets "panghu-avatar.ico"
$appName = [string]::Concat([char]0x80D6, [char]0x864E, "AI", [char]0x591A, "Agent", [char]0x4E00, [char]0x952E, [char]0x90E8, [char]0x7F72, [char]0x5DE5, [char]0x5177)
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-build.txt
$certifiData = & $python -c "import certifi, pathlib; print(pathlib.Path(certifi.where()).parent)"
$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", $appName,
    "--icon", $icon,
    "--add-data", "$certifiData;certifi",
    "--add-data", "$($assets);assets",
    "--distpath", "release",
    "--workpath", "build",
    "--specpath", "build",
    "src\panghu_codex_installer.py"
)
& $python @pyinstallerArgs
$releaseDir = Join-Path (Join-Path $root "release") $appName
$zip = Join-Path (Join-Path $root "release") "$($appName)-Windows.zip"
if (Test-Path -LiteralPath $zip) {
    Remove-Item -LiteralPath $zip -Force
}
Compress-Archive -LiteralPath $releaseDir -DestinationPath $zip -Force
Write-Host "Build finished."
Write-Host (Join-Path $releaseDir "$appName.exe")
Write-Host $zip
