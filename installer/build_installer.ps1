# Build PyInstaller output, then compile the Inno Setup installer (if ISCC is available).
# Run from pos-system:  powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
# Optional: pass install code without editing the .iss file:
#   .\installer\build_installer.ps1 -InstallCode "YourSecret"

param(
    [string] $InstallCode = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> PyInstaller (one-folder). Close SmartStock.exe if open (folder must not be locked)."
python -m PyInstaller -y smartstock.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$readme = Join-Path $Root "V01_README.txt"
$distApp = Join-Path $Root "dist\V01"
if (Test-Path $readme) {
    Copy-Item -LiteralPath $readme -Destination (Join-Path $distApp "V01_README.txt") -Force
}
if (-not (Test-Path (Join-Path $distApp "SmartStock.exe"))) {
    Write-Error "Expected SmartStock.exe under $distApp"
}

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warning "Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php then re-run this script, or compile installer\SmartStock.iss manually."
    exit 0
}

$iss = Join-Path $PSScriptRoot "SmartStock.iss"
if ($InstallCode) {
    Write-Host "==> Inno Setup (ISCC) with /DINSTALL_CODE=***..."
    & $iscc "/DINSTALL_CODE=$InstallCode" $iss
} else {
    Write-Host "==> Inno Setup (ISCC) — using INSTALL_CODE from SmartStock.iss (default define)..."
    & $iscc $iss
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done. Setup executable: $(Join-Path $Root 'dist_installer\SmartStock_Setup.exe')"
