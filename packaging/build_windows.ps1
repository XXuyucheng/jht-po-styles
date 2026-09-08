# Build Windows portable folder with PyInstaller (run on Windows).
# Usage (PowerShell, from repo root):
#   .\packaging\build_windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Creating venv (if needed)"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Pip = Join-Path $Root ".venv\Scripts\pip.exe"

Write-Host "==> Installing dependencies"
& $Pip install -U pip
& $Pip install -r requirements.txt -r requirements-build.txt
# Chromium is downloaded on first extract into %LOCALAPPDATA%\jht-po-styles\ms-playwright

Write-Host "==> Cleaning previous build"
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

Write-Host "==> PyInstaller"
& $Py -m PyInstaller packaging\jht_po_styles.spec --noconfirm --clean

$Dist = Join-Path $Root "dist\JhtPoStyles"
if (-not (Test-Path $Dist)) {
    throw "Build failed: $Dist not found"
}

Copy-Item (Join-Path $PSScriptRoot "JhtPoStyles.bat") (Join-Path $Dist "JhtPoStyles.bat") -Force

$Zip = Join-Path $Root "dist\JhtPoStyles-windows-portable.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path (Join-Path $Dist "*") -DestinationPath $Zip

Write-Host ""
Write-Host "Done."
Write-Host "  App folder: $Dist"
Write-Host "  Portable zip: $Zip"
Write-Host "Run: $Dist\JhtPoStyles.exe   (or JhtPoStyles.bat)"
Write-Host "IMPORTANT: put the folder on an ASCII path, e.g. C:\Tools\JhtPoStyles\"
Write-Host "First extract will download Chromium into %LOCALAPPDATA%\jht-po-styles\ms-playwright"
Write-Host ""
Write-Host "Optional installer: open packaging\installer.iss in Inno Setup and Compile."
