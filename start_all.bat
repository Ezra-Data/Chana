@echo off
title Chana - Launcher
echo ======================================================
echo Launching Chana: Chatbot & Navigation System
echo ======================================================
start "Chana - Backend" cmd /k "%~dp0start_backend.bat"
start "Chana - Frontend" cmd /k "%~dp0start_frontend.bat"
echo.
echo Both servers launched in separate windows!
echo - Backend:  http://127.0.0.1:8000 (Docs: http://127.0.0.1:8000/docs)
echo - Frontend: http://127.0.0.1:5173
echo ======================================================
timeout /t 5
