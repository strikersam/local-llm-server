@echo off
REM Cross-platform Claude Code launcher (Windows entry point)
REM Auto-detects OS and executes with proper error handling

cd /d "%~dp0"

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found in PATH
    echo Please install Python 3 from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Execute the Python launcher, passing through all arguments
python run-claude-code.py %*
exit /b %ERRORLEVEL%
