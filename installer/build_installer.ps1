# Build SmartStock_Setup.exe with Inno Setup 6 (run from pos-system).
# Usage:
#   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
#   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1 -InstallCode "YourSecret"

param(
    [string]$InstallCode = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

$distV01 = Join-Path $Root "dist\V01"
$exe = Join-Path $distV01 "SmartStock.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    Write-Host "==> dist\V01\SmartStock.exe not found - running PyInstaller ..."
    & (Join-Path $Root "tools\build_v1.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$candidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Error "Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php (ISCC.exe expected under Program Files)."
    exit 1
}

$iss = Join-Path $Root "installer\SmartStock.iss"
Write-Host "==> Inno Setup -> dist\SmartStock_Setup.exe ..."
if ($InstallCode) {
    $escapedInstallCode = $InstallCode.Replace('"', '\"')
    $installCodeArg = "/DINSTALL_CODE=""$escapedInstallCode"""
    & $iscc $iss $installCodeArg
} else {
    & $iscc $iss
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$out = Join-Path $Root "dist\SmartStock_Setup.exe"
if (Test-Path -LiteralPath $out) {
    Write-Host "Done:"
    Write-Host "  $out"
} else {
    Write-Error "Expected output not found: $out"
    exit 1
}
