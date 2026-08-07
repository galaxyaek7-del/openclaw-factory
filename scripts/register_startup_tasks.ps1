# Registers Galaxy Forge's two critical services (factory_loop.js, server.js)
# as Windows Scheduled Tasks so they survive reboot, logoff, VS Code closing,
# and Claude Code restarting -- none of which scripts/supervisor.js alone can
# do, since it is only a Node process that itself needs something to start it.
#
# This does NOT replace scripts/supervisor.js. It wraps it: Task Scheduler's
# job is only to get supervisor.js running again after a reboot/logon and to
# restart supervisor.js itself if the whole process tree dies; supervisor.js
# keeps doing what it already does -- fast, crash-loop-guarded restarts of
# the target script without needing a full OS-level restart cycle for every
# ordinary crash. Two layers, each doing the one job it's already built for.
#
# NOT run automatically. Registering a task that auto-executes real code
# (including real Groq API calls) at every boot/logon, indefinitely, without
# an active work session, is a standing decision -- run this manually, once
# reviewed, when you want that behavior turned on permanently.
#
# To remove later:
#   Unregister-ScheduledTask -TaskName "GalaxyForge-FactoryLoop" -Confirm:$false
#   Unregister-ScheduledTask -TaskName "GalaxyForge-Server" -Confirm:$false

$RepoDir = "C:\openclaw-dasgboard"
$NodeExe = (Get-Command node).Source

function Register-GalaxyForgeTask {
    param(
        [string]$TaskName,
        [string]$SupervisorTarget
    )

    $action = New-ScheduledTaskAction `
        -Execute $NodeExe `
        -Argument "scripts\supervisor.js" `
        -WorkingDirectory $RepoDir

    # Fires at boot AND at logon, so it starts whichever happens first.
    $triggers = @(
        (New-ScheduledTaskTrigger -AtStartup),
        (New-ScheduledTaskTrigger -AtLogOn)
    )

    $settings = New-ScheduledTaskSettingsSet `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -StartWhenAvailable `
        -DontStopOnIdleEnd `
        -ExecutionTimeLimit (New-TimeSpan -Days 0) `
        -MultipleInstances IgnoreNew

    # SUPERVISOR_TARGET is passed via an environment-variable-setting
    # principal action isn't directly supported by New-ScheduledTaskAction,
    # so it's set on the task's own registration via -Argument is not
    # sufficient either -- Task Scheduler actions don't take env vars
    # directly. Instead, wrap through cmd.exe to set it inline.
    $action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c set SUPERVISOR_TARGET=$SupervisorTarget&& `"$NodeExe`" scripts\supervisor.js >> logs\$($SupervisorTarget.Replace('.js',''))_supervised.log 2>&1" `
        -WorkingDirectory $RepoDir

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $triggers `
        -Settings $settings `
        -Description "Galaxy Forge: keeps $SupervisorTarget running via scripts/supervisor.js across reboot/logon/crash. See CLAUDE.md's Running the project section." `
        -RunLevel Limited `
        -Force
}

Register-GalaxyForgeTask -TaskName "GalaxyForge-FactoryLoop" -SupervisorTarget "factory_loop.js"
Register-GalaxyForgeTask -TaskName "GalaxyForge-Server" -SupervisorTarget "server.js"

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'GalaxyForge-*'"
Write-Host "Test without rebooting: Start-ScheduledTask -TaskName 'GalaxyForge-FactoryLoop'"
