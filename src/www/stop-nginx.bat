@echo off
REM ============================================
REM  37AC front-end stop script
REM  Stops Nginx and all PHP-CGI instances.
REM  NOTE: Keep this file ASCII-only! cmd.exe
REM  parses batch files with GBK codepage; UTF-8
REM  Chinese comments cause byte misalignment.
REM ============================================
setlocal

set NGINX_DIR=C:\tools\nginx

echo Stopping 37AC front-end (Nginx + PHP-CGI)...

REM --- 1. Stop Nginx ---
taskkill /IM nginx.exe /F >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] Nginx stopped
) else (
    echo   [INFO] Nginx not running
)

REM --- 2. Stop all php-cgi instances ---
taskkill /IM php-cgi.exe /F >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] PHP-CGI instances stopped
) else (
    echo   [INFO] PHP-CGI not running
)

echo.
echo Done.
pause