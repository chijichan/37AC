@echo off
REM ============================================
REM  37AC front-end start script (Nginx + PHP-CGI)
REM  Windows has no PHP-FPM, so 4 php-cgi instances
REM  form a process pool: SSE long connections will
REM  not block other requests.
REM  Uses php-cgi.ini (Xdebug disabled + opcache on).
REM  NOTE: Keep this file ASCII-only! cmd.exe parses
REM  batch files with GBK codepage; UTF-8 Chinese
REM  comments cause byte misalignment and break
REM  keywords like setlocal / for /L.
REM ============================================
setlocal enabledelayedexpansion

set NGINX_DIR=C:\tools\nginx
set PHP_CGI=E:\apps\PHP\php-cgi.exe
set PHP_INI=E:\apps\PHP\php-cgi.ini
set CGI_BASE_PORT=9001
set CGI_COUNT=4

echo Starting 37AC front-end (Nginx + PHP-CGI)...
echo Server will run at: http://localhost:8000
echo.

REM --- 1. Check port 8000 is free ---
netstat -ano | findstr ":8000 " >nul 2>&1
if %errorlevel%==0 (
    echo [ERROR] Port 8000 is already in use. Stop the old server first.
    exit /b 1
)

REM --- 2. Start PHP-CGI process pool ---
for /L %%i in (1,1,%CGI_COUNT%) do (
    set /a PORT=%CGI_BASE_PORT% + %%i - 1
    start "php-cgi-!PORT!" /B "%PHP_CGI%" -b 127.0.0.1:!PORT! -c "%PHP_INI%"
    echo   [OK] php-cgi instance started on port !PORT!
)

REM --- 3. Start Nginx ---
cd /d "%NGINX_DIR%"
REM NOTE: The -p prefix must NOT end with a backslash.
REM A trailing backslash before the closing quote is
REM treated as an escaped quote by cmd, producing a
REM wrong prefix (e.g. C:\tools\nginx") and nginx fails.
start "nginx" /B "%NGINX_DIR%\nginx.exe" -p "%NGINX_DIR%"
echo   [OK] Nginx started
echo.
echo All services started. Keep this window open.
echo Stop with: stop-nginx.bat
pause