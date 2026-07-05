@echo off
cd C:\openclaw-dasgboard
echo Starting OpenClaw Factory...
start "n8n" cmd /c "cd /d C:\Users\%USERNAME%\AppData\Roaming\npm && npx n8n start"
timeout /t 5
start "Dashboard" node server.js
timeout /t 3
start "Factory Loop" node factory_loop.js
echo === OpenClaw Factory RUNNING ===
echo Dashboard: http://localhost:3000
echo n8n: http://localhost:5678
pause
