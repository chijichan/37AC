@echo off
REM ============================================
REM  37AC 前端站点停止脚本
REM  停止 Nginx 与所有 PHP-CGI 实例
REM ============================================
setlocal

set NGINX_DIR=C:\tools\nginx

echo Stopping 37AC front-end (Nginx + PHP-CGI)...

REM --- 1. 停止 Nginx ---
taskkill /IM nginx.exe /F >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] Nginx stopped
) else (
    echo   [INFO] Nginx not running
)

REM --- 2. 停止所有 php-cgi 实例 ---
taskkill /IM php-cgi.exe /F >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] PHP-CGI instances stopped
) else (
    echo   [INFO] PHP-CGI not running
)

echo.
echo Done.
pause
