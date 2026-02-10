@echo off
echo Starting PHP Development Server...
echo Server will run at: http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
cd public
php -S localhost:8000
