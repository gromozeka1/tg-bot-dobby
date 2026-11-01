$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    throw "Missing .env. Copy .env.example to .env and configure BOT_TOKEN."
}
if (-not (Test-Path $Python)) {
    throw "Missing virtual environment. Run: py -3.14 -m venv .venv; .\.venv\Scripts\python -m pip install -e ."
}

$DelaySeconds = 5
$MaximumDelaySeconds = 300
while ($true) {
    Write-Output "Starting Dobby..."
    Push-Location $ProjectRoot
    try {
        & $Python -m dobby
        $ExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    Write-Warning "Dobby exited with code $ExitCode. Restarting in $DelaySeconds seconds."
    Start-Sleep -Seconds $DelaySeconds
    $DelaySeconds = [Math]::Min($DelaySeconds * 2, $MaximumDelaySeconds)
}
