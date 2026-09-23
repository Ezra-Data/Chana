@echo off
title Chana - Backend (FastAPI)
cd /d "%~dp0backend"
echo Starting Chana Backend on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
