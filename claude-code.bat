@echo off
REM Quick command to launch Claude Code with local proxy setup
REM For detailed instructions, see: docs/claude-code-setup.md

cd /d "%~dp0"

REM Check if PowerShell script exists
if not exist "launch-claude-code.ps1" (
    echo Error: launch-claude-code.ps1 not found
    exit /b 1
)

REM Execute the PowerShell script, passing through all arguments
powershell -NoProfile -ExecutionPolicy Bypass -File "launch-claude-code.ps1" %*
