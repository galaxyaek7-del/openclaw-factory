# One-time, run by the founder: register a logon task that starts the factory
# (server.js + factory_loop.js under the supervisor) via
# scripts/start_factory_supervised.ps1, which never starts a second copy.
# Mirrors the existing GalaxyForge-N8N-Autostart task. Undo with:
#   Unregister-ScheduledTask -TaskName 'GalaxyForge-Factory-Autostart' -Confirm:$false
$a = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument '-NoProfile -WindowStyle Hidden -File "C:\openclaw-dasgboard\scripts\start_factory_supervised.ps1"' `
  -WorkingDirectory 'C:\openclaw-dasgboard'
$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$t.Delay = 'PT1M'
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName 'GalaxyForge-Factory-Autostart' -Action $a -Trigger $t -Settings $s `
  -Description 'Starts server.js and factory_loop.js under scripts/supervisor.js at logon; skips any already running.' |
  Select-Object TaskName, State
