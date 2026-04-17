@echo off
setlocal
:: Starts an ngrok tunnel pointing at the proxy port.
:: Uses NGROK_EXE from .env/environment, or searches PATH and default pyngrok install location.
:: If NGROK_DOMAIN is set, uses it as the static domain (--domain flag).

if "%PROXY_PORT%"=="" set PROXY_PORT=8000

:: Resolve ngrok binary without goto/labels so startup works reliably under
:: redirected, non-interactive launches from PowerShell.
if "%NGROK_EXE%"=="" (
    if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" (
        set "NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe"
    ) else (
        set "NGROK_EXE=ngrok"
    )
)

if not exist "%NGROK_EXE%" (
    where "%NGROK_EXE%" >nul 2>nul
    if errorlevel 1 (
        echo [FAIL] ngrok executable not found: %NGROK_EXE%
        exit /b 1
    )
)

if not "%NGROK_DOMAIN%"=="" (
    "%NGROK_EXE%" http %PROXY_PORT% --url=%NGROK_DOMAIN% --log=stderr
) else (
    "%NGROK_EXE%" http %PROXY_PORT% --log=stderr
)
