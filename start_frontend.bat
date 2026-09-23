@echo off
title Chana - Frontend (Vite)
cd /d "%~dp0frontend"
echo Setting local Node.js environment...
set "PATH=%~dp0.node\node-v20.18.0-win-x64;%PATH%"
echo Starting Chana Frontend on http://127.0.0.1:5173 ...
call npm run dev -- --host 127.0.0.1 --port 5173
pause
