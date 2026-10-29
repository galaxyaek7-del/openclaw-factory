@echo off
rem Start the factory safely (2026-10-29). The old version started server.js and
rem factory_loop.js WITHOUT the supervisor and with no duplicate guard (double-
rem clicking it while the factory ran started a second copy of everything).
rem It now delegates to scripts\start_factory_supervised.ps1, which starts each
rem process under scripts\supervisor.js only if it is not already running, and to
rem the existing n8n logon task, which refuses to start a second n8n.
cd /d C:\openclaw-dasgboard
powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'GalaxyForge-N8N-Autostart'" 2>nul
powershell -NoProfile -File scripts\start_factory_supervised.ps1
echo Dashboard: http://localhost:3000   n8n: http://localhost:5678
