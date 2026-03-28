@echo off
:: Starts the FastAPI auth proxy.
:: All settings are read from environment variables (set in .env / start_server.ps1).

if "%API_KEYS%"==""        set API_KEYS=change-me
if "%OLLAMA_BASE%"==""     set OLLAMA_BASE=http://localhost:11434
if "%PROXY_PORT%"==""      set PROXY_PORT=8000
if "%RATE_LIMIT_RPM%"==""  set RATE_LIMIT_RPM=60
if "%LOG_LEVEL%"==""       set LOG_LEVEL=INFO

if "%PYTHON_EXE%"=="" (
    python -m uvicorn proxy:app --host 0.0.0.0 --port %PROXY_PORT%
) else (
    "%PYTHON_EXE%" -m uvicorn proxy:app --host 0.0.0.0 --port %PROXY_PORT%
)
