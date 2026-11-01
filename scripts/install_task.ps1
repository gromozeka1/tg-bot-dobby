param(
    [string]$TaskName = "DobbyBot",
    [string]$BackupTaskName = "DobbyDatabaseBackup",
    [switch]$SkipBackupTask
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RunScript = Join-Path $ProjectRoot "scripts\run_bot.ps1"
$BackupScript = Join-Path $ProjectRoot "scripts\backup_db.py"

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    throw "Missing .env. Copy .env.example to .env and configure BOT_TOKEN first."
}
if (-not (Test-Path $Python)) {
    throw "Missing virtual environment or package. Install dependencies with pip install -e ."
}

$Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal -UserId $Identity -LogonType Interactive -RunLevel Limited
$BotAction = New-ScheduledTaskAction `
    -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunScript`"" `
    -WorkingDirectory $ProjectRoot
$LogonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $Identity
$BotSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $BotAction `
    -Trigger $LogonTrigger `
    -Principal $Principal `
    -Settings $BotSettings `
    -Description "Run the Dobby Telegram bot after this user logs on." `
    -Force | Out-Null

if (-not $SkipBackupTask) {
    $BackupAction = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument "`"$BackupScript`"" `
        -WorkingDirectory $ProjectRoot
    $BackupTrigger = New-ScheduledTaskTrigger -Daily -At "3:00AM"
    $BackupSettings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)

    Register-ScheduledTask `
        -TaskName $BackupTaskName `
        -Action $BackupAction `
        -Trigger $BackupTrigger `
        -Principal $Principal `
        -Settings $BackupSettings `
        -Description "Create a verified SQLite online backup for Dobby." `
        -Force | Out-Null
}

Write-Output "Registered task '$TaskName' for $Identity."
if (-not $SkipBackupTask) {
    Write-Output "Registered daily backup task '$BackupTaskName' (3:00 AM)."
}
