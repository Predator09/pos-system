# Called by SmartStock Inno Setup after install - writes the same marker checked at runtime.
$ErrorActionPreference = "Stop"

try {
    if (-not $env:LOCALAPPDATA) {
        throw "LOCALAPPDATA is not available."
    }

    $p = Join-Path -Path $env:LOCALAPPDATA -ChildPath "SmartStock\.install_verified"
    $dir = Split-Path -LiteralPath $p
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }

    $json = (@{ verified_at = [DateTime]::UtcNow.ToString("o") } | ConvertTo-Json -Compress)
    Set-Content -LiteralPath $p -Value $json -Encoding utf8

    if (-not (Test-Path -LiteralPath $p)) {
        throw "Install verification marker was not created at '$p'."
    }
} catch {
    Write-Error "Failed to write install verification marker: $_"
    exit 1
}
