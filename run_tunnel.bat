@echo off
:: Starts an ngrok tunnel pointing at the proxy port.
:: Uses NGROK_EXE from .env/environment, or searches PATH and default pyngrok install location.
:: If NGROK_DOMAIN is set, uses it as the static domain (--domain flag).

if "%PROXY_PORT%"=="" set PROXY_PORT=8000

:: Resolve ngrok binary
if not "%NGROK_EXE%"=="" goto :have_ngrok
if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" (
    set NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe
    goto :have_ngrok
)
set NGROK_EXE=ngrok

:have_ngrok
if not "%NGROK_DOMAIN%"=="" (
    "%NGROK_EXE%" http %PROXY_PORT% --url=%NGROK_DOMAIN% --log=stderr
) else (
    "%NGROK_EXE%" http %PROXY_PORT% --log=stderr
)
