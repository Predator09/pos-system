# Build portable app into dist\V01\ (run from repo root: pos-system).
# Usage:  powershell -ExecutionPolicy Bypass -File tools\build_v1.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> PyInstaller -> dist\V01 ..."
python -m PyInstaller -y smartstock.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$readme = Join-Path $Root "V01_README.txt"
$destDir = Join-Path $Root "dist\V01"
if (Test-Path $readme) {
    Copy-Item -LiteralPath $readme -Destination (Join-Path $destDir "V01_README.txt") -Force
    Write-Host "==> Copied V01_README.txt next to SmartStock.exe"
}

Write-Host "Done. Copy the entire folder to another PC:"
Write-Host "  $destDir"
