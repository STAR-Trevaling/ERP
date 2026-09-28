@echo off
echo ==========================================
echo Running Pytest TDD Suite
echo ==========================================
cd /d "%~dp0"
.\.venv\Scripts\pytest -v backend
pause
