<#
.SYNOPSIS
  Registers (or updates) the Windows scheduled task that runs the tracker.

.DESCRIPTION
  Runs scripts/track-and-pr.ps1 every Monday and Thursday at 09:00 while you
  are logged on. If the PC was off or asleep at that time, it runs as soon as
  possible afterwards. Remove it with:
    Unregister-ScheduledTask -TaskName "EO Training Atlas tracker"
#>
$repo = Split-Path $PSScriptRoot -Parent
$python = (Get-Command python -ErrorAction Stop).Source
$script = Join-Path $PSScriptRoot "track-and-pr.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $repo `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Python `"$python`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Thursday -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "EO Training Atlas tracker" -Force -Action $action -Trigger $trigger -Settings $settings `
    -Description "Runs the ARSET tracker and opens a pull request with new trainings, recordings and materials." | Out-Null
Get-ScheduledTask -TaskName "EO Training Atlas tracker" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
