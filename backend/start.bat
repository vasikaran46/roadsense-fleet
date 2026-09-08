@echo off
REM RoadSense Fleet — Start Server
cd /d "%~dp0"
echo Starting RoadSense Fleet server...
"%~dp0venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
