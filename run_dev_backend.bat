@echo off
echo ==========================================
echo Starting FastAPI Middleware on Port 8000
echo ==========================================
cd /d "%~dp0backend"
call ..\.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
