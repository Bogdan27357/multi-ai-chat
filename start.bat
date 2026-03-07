@echo off
chcp 65001 >nul
echo Запуск Multi-AI Chat...
echo.

:: Activate venv
call .venv\Scripts\activate.bat

:: Start Ollama in background
echo Запуск Ollama...
start /min "" ollama serve

:: Wait a moment for Ollama to start
timeout /t 3 /noq >nul

:: Start the app
echo Запуск сервера на http://localhost:8000
echo Нажмите Ctrl+C для остановки.
echo.
start http://localhost:8000
uvicorn app.main:app --reload --port 8000
