# Start the factory's two long-running processes under scripts/supervisor.js,
# skipping any that is already running (2026-10-29).
#
# Why: server.js and factory_loop.js were started by hand on 2026-10-17
# (`cmd /c node scripts\supervisor.js >> logs\...`) and nothing restarts them
# after a reboot or log-off. start_factory.bat is not safe for this: it starts
# both WITHOUT the supervisor, has no duplicate guard, starts n8n without its
# environment, and ends with `pause`. n8n has its own logon task
# (GalaxyForge-N8N-Autostart) and is not started here.
#
# Guards (no second copy is ever started):
#   server -> skipped if something listens on 127.0.0.1:3000 or a supervisor
#             whose log is server_supervised.log is running;
#   loop   -> skipped if a node process runs factory_loop.js.
#
#   powershell -NoProfile -File scripts\start_factory_supervised.ps1 [-DryRun]
param([switch]$DryRun)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine }

function Start-Supervised($label, $log, $target) {
  $cmd = "node scripts\supervisor.js >> logs\$log 2>&1"
  if ($DryRun) { Write-Output "[dry-run] would start $label supervisor: $cmd (SUPERVISOR_TARGET=$target)"; return }
  if ($target) { $env:SUPERVISOR_TARGET = $target } else { Remove-Item Env:SUPERVISOR_TARGET -ErrorAction SilentlyContinue }
  Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -WorkingDirectory $root -WindowStyle Hidden
  Remove-Item Env:SUPERVISOR_TARGET -ErrorAction SilentlyContinue
  Write-Output "started $label supervisor"
}

$serverListening = $false
try { $serverListening = [bool](Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction Stop) } catch {}
$serverSupervisor = $procs | Where-Object { $_.CommandLine -match 'supervisor\.js' -and $_.CommandLine -match 'server_supervised\.log' }
if ($serverListening -or $serverSupervisor) {
  Write-Output "server: already running (port 3000 listening=$serverListening) - not started"
} else {
  Start-Supervised 'server' 'server_supervised.log' $null
}

$loop = $procs | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'factory_loop\.js' }
$loopSupervisor = $procs | Where-Object { $_.CommandLine -match 'supervisor\.js' -and $_.CommandLine -match 'factory_loop_supervised\.log' }
if ($loop -or $loopSupervisor) {
  Write-Output "factory_loop: already running - not started"
} else {
  Start-Supervised 'factory_loop' 'factory_loop_supervised.log' 'factory_loop.js'
}
