# Registers SME_API and SME_Streamlit as Windows scheduled tasks that run
# at every user logon, hidden, with auto-restart on failure.
#
# Re-run this script after pulling new launcher scripts; it overwrites
# any existing task with the same name.
#
# Uninstall:  schtasks /Delete /TN SME_API /F ; schtasks /Delete /TN SME_Streamlit /F

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$User = "$env:USERDOMAIN\$env:USERNAME"

function Register-Task {
    param([string]$Name, [string]$Script)
    $exe = "powershell.exe"
    $args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Repo\scripts\$Script`""

    $action  = New-ScheduledTaskAction  -Execute $exe -Argument $args
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $User
    $settings = New-ScheduledTaskSettingsSet `
                    -AllowStartIfOnBatteries `
                    -DontStopIfGoingOnBatteries `
                    -StartWhenAvailable `
                    -RestartCount 99 `
                    -RestartInterval (New-TimeSpan -Minutes 1) `
                    -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    $principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $Name `
                           -Action $action -Trigger $trigger `
                           -Settings $settings -Principal $principal `
                           -Force | Out-Null
    Write-Output "registered  $Name"
}

Register-Task -Name "SME_API"        -Script "start_local_api.ps1"
Register-Task -Name "SME_Streamlit"  -Script "start_local_streamlit.ps1"

Write-Output ""
Write-Output "Starting both tasks now…"
Start-ScheduledTask -TaskName "SME_API"
Start-ScheduledTask -TaskName "SME_Streamlit"
Start-Sleep -Seconds 8

Write-Output ""
Write-Output "Status:"
Get-ScheduledTask -TaskName "SME_API","SME_Streamlit" |
    Get-ScheduledTaskInfo |
    Select-Object TaskName, LastRunTime, LastTaskResult, NumberOfMissedRuns |
    Format-Table -AutoSize
