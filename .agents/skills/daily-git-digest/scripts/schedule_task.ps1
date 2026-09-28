<#
.SYNOPSIS
    Manages a Windows Scheduled Task for Daily Git Digest automated execution.

.DESCRIPTION
    Provides automated Register, Status, and Unregister actions for running the
    Daily Git Digest script on an automated daily schedule.

.PARAMETER Action
    Register, Status, RunNow, or Unregister.

.PARAMETER DailyTime
    Daily execution time (e.g. "09:00"). Default is "09:00".

.PARAMETER RepoPath
    Target repository path to audit. Defaults to the repository root.
#>

param (
    [ValidateSet("Register", "Status", "RunNow", "Unregister")]
    [string]$Action = "Status",
    
    [string]$DailyTime = "09:00",
    
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..\..\..").Path
)

$TaskName = "DailyGitDigest-$((Get-Item $RepoPath).Name)"
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
$ScriptPath = Join-Path $PSScriptRoot "digest_generator.py"

if (-not $PythonExe) {
    Write-Error "Python executable was not found in PATH."
    exit 1
}

switch ($Action) {
    "Register" {
        Write-Host "Registering daily scheduled task '$TaskName' at $DailyTime..." -ForegroundColor Cyan
        
        $ArgumentList = "`"$ScriptPath`" --repo-path `"$RepoPath`" --output-dir `"reports`" --update-release-notes"
        $TaskAction = New-ScheduledTaskAction -Execute $PythonExe -Argument $ArgumentList -WorkingDirectory $RepoPath
        
        $TimeParts = $DailyTime.Split(":")
        $TriggerTime = (Get-Date).Date.AddHours([int]$TimeParts[0]).AddMinutes([int]$TimeParts[1])
        $TaskTrigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime
        
        $TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        
        Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $TaskTrigger -Settings $TaskSettings -Description "Runs Daily Git & Project Digest generation" -Force
        
        Write-Host "✅ Task successfully registered. It will trigger daily at $DailyTime." -ForegroundColor Green
    }
    
    "Status" {
        Write-Host "Checking status for task '$TaskName'..." -ForegroundColor Cyan
        $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($Task) {
            $Info = Get-ScheduledTaskInfo -TaskName $TaskName
            Write-Host "Task Name:    $($Task.TaskName)"
            Write-Host "State:        $($Task.State)"
            Write-Host "Last Run:     $($Info.LastRunTime)"
            Write-Host "Last Result:  $($Info.LastTaskResult)"
            Write-Host "Next Run:     $($Info.NextRunTime)"
        } else {
            Write-Host "Task '$TaskName' is not registered." -ForegroundColor Yellow
            Write-Host "To register, run: .\schedule_task.ps1 -Action Register -DailyTime `"09:00`""
        }
    }

    "RunNow" {
        Write-Host "Executing task '$TaskName' immediately..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ Task triggered." -ForegroundColor Green
    }

    "Unregister" {
        Write-Host "Unregistering task '$TaskName'..." -ForegroundColor Cyan
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "✅ Task unregistered." -ForegroundColor Green
    }
}
