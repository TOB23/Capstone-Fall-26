<#
  register_task.ps1 - register the outage collector as a Windows scheduled task.

  Run ONCE to install the schedule. After that, Windows Task Scheduler runs the
  collector automatically; you do not run this again unless you change settings.

  HOW TO RUN:
    1. Edit run_collector.bat first (set REPO_DIR and PYTHON).
    2. Open PowerShell  (no admin needed for a per-user task).
    3. cd into the repo folder.
    4. Run:   powershell -ExecutionPolicy Bypass -File register_task.ps1

  WHAT IT DOES:
    Creates a task named "OutageCollector" that runs run_collector.bat every
    IntervalMinutes (default 60 - hourly, matching the HRRR cadence).

  Other commands once installed:
    Start now :  Start-ScheduledTask -TaskName "OutageCollector"
    Check it  :  Get-ScheduledTask -TaskName "OutageCollector" | Get-ScheduledTaskInfo
    Remove it :  Unregister-ScheduledTask -TaskName "OutageCollector" -Confirm:$false
#>

param(
    [int]$IntervalMinutes = 60,                 # 60 = hourly. 15 = EAGLE-I cadence.
    [string]$TaskName     = "OutageCollector"
)

$ErrorActionPreference = "Stop"

# The .bat sits next to this script.
$batPath = Join-Path $PSScriptRoot "run_collector.bat"
if (-not (Test-Path $batPath)) {
    Write-Error "run_collector.bat not found next to this script. Aborting."
    exit 1
}

Write-Host "Registering task '$TaskName'"
Write-Host "  runs : $batPath"
Write-Host "  every: $IntervalMinutes minutes"

# Action: run the batch wrapper.
$action = New-ScheduledTaskAction -Execute $batPath

# Trigger: start now, then repeat forever at the chosen interval.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

# Settings:
#   StartWhenAvailable - if a run is missed (machine was off/asleep), run as
#                        soon as possible afterward instead of skipping silently.
#   WakeToRun          - wake the machine from SLEEP to run (cannot wake from
#                        full shutdown - nothing can).
#   no idle/battery stops - keep collecting on a laptop on battery.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew          # if a pass overruns, skip the next, don't stack

# Run as the current user, only when logged on (no stored password needed).
# To run even when logged off, register with -User/-Password instead.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask -TaskName $TaskName `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Runs one national outage collection pass for Capstone verification." `
    -Force | Out-Null

Write-Host ""
Write-Host "Done. Task '$TaskName' is registered and will run every $IntervalMinutes min."
Write-Host "Run one pass now to test:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Then check logs\ for collector_<date>.log"
