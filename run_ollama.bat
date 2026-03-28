@echo off
:: Starts Ollama with the configured model directory.
:: OLLAMA_EXE and OLLAMA_MODELS are read from the environment (set in .env / start_server.ps1).
:: Falls back to "ollama" on PATH if OLLAMA_EXE is not set.

if "%OLLAMA_MODELS%"=="" set OLLAMA_MODELS=D:\aipc-models
if "%OLLAMA_HOST%"==""   set OLLAMA_HOST=127.0.0.1:11434

if "%OLLAMA_EXE%"=="" (
    ollama serve
) else (
    "%OLLAMA_EXE%" serve
)
