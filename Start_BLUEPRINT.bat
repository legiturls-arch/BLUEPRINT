@echo off
cd /d D:\BLUEPRINT
call .venv\Scripts\activate.bat
python -m uvicorn app:app --reload
pause
