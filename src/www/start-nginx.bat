@echo off
REM ============================================
REM  37AC front-end start (Nginx + PHP-CGI pool)
REM  Site: http://localhost:8000
REM  Services start HIDDEN & DETACHED (no cmd
REM  windows; VS Code terminal stays free; close
REM  terminal will NOT stop services).
REM  No hardcoded paths: resolves nginx/php-cgi
REM  from env vars (NGINX_HOME / PHP_HOME) or PATH.
REM  ASCII-only file (cmd uses OEM codepage)
REM ============================================
setlocal enabledelayedexpansion

set CGI_BASE_PORT=9001
set CGI_COUNT=4

echo Starting 37AC front-end (hidden, background)...
echo Site: http://localhost:8000
echo.

REM --- Resolve nginx.exe (NGINX_HOME first, then PATH) ---
set "NGINX_EXE="
if defined NGINX_HOME if exist "%NGINX_HOME%\nginx.exe" set "NGINX_EXE=%NGINX_HOME%\nginx.exe"
if not defined NGINX_EXE for /f "delims=" %%i in ('where nginx 2^>nul') do if not defined NGINX_EXE set "NGINX_EXE=%%i"
if not defined NGINX_EXE (
    echo [ERROR] nginx.exe not found. Add nginx dir to PATH or set NGINX_HOME.
    exit /b 1
)
for %%i in ("%NGINX_EXE%") do set "NGINX_PREFIX=%%~dpi"
set "NGINX_PREFIX=%NGINX_PREFIX:~0,-1%"
echo   [OK] nginx: %NGINX_EXE%

REM --- Resolve php-cgi.exe (PHP_HOME first, then PATH) ---
set "PHP_EXE="
if defined PHP_HOME if exist "%PHP_HOME%\php-cgi.exe" set "PHP_EXE=%PHP_HOME%\php-cgi.exe"
if not defined PHP_EXE for /f "delims=" %%i in ('where php-cgi 2^>nul') do if not defined PHP_EXE set "PHP_EXE=%%i"
if not defined PHP_EXE (
    echo [ERROR] php-cgi.exe not found. Add PHP dir to PATH or set PHP_HOME.
    exit /b 1
)
for %%i in ("%PHP_EXE%") do set "PHP_DIR=%%~dpi"
set "PHP_INI=%PHP_DIR%php-cgi.ini"
if not exist "%PHP_INI%" set "PHP_INI="
echo   [OK] php-cgi: %PHP_EXE%

echo.

REM --- Free port 8000 first (kills whatever holds it) ---
call "%~dp0stop-nginx.bat" -q

REM --- Start PHP-CGI pool (9001..9004), hidden & detached ---
for /L %%i in (1,1,%CGI_COUNT%) do (
    set /a PORT=%CGI_BASE_PORT% + %%i - 1
    if defined PHP_INI (
        powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%PHP_EXE%' -ArgumentList '-b','127.0.0.1:!PORT!','-c','%PHP_INI%'"
    ) else (
        powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%PHP_EXE%' -ArgumentList '-b','127.0.0.1:!PORT!'"
    )
    echo   [OK] php-cgi on port !PORT!
)

REM --- Start Nginx, hidden & detached ---
REM NOTE: -p prefix must NOT end with a backslash.
powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%NGINX_EXE%' -ArgumentList '-p','%NGINX_PREFIX%'"
echo   [OK] Nginx started

echo.
echo All services are running in the background (no windows).
echo Site: http://localhost:8000   Stop with: stop-nginx.bat
