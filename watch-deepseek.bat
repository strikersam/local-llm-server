@echo off
REM Real-time DeepSeek 32B Ollama logger
title DeepSeek 32B - Real-Time Logs
color 0A

echo.
echo ========================================
echo   DeepSeek 32B Real-Time Log Monitor
echo ========================================
echo.

cd /d C:\Users\swami\qwen-server

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Make sure Python is installed and in PATH.
    pause
    exit /b 1
)

REM Run the monitor
python tail_ollama_realtime.py

pause
