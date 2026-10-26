@echo off
title Face Attendance - Auto Setup and Run
color 0A

echo.
echo =====================================================
echo   FACE ATTENDANCE SYSTEM - AUTO SETUP
echo =====================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11 from:
    echo https://www.python.org/downloads/release/python-3119/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b
)

echo [OK] Python found.
python --version

:: Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found. Reinstall Python with pip included.
    pause
    exit /b
)

echo.
echo [1/4] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo.
echo [2/4] Installing packages (this may take 5-10 minutes)...
echo       Please wait...
echo.

:: Install dlib first (try pre-built)
echo Installing dlib...
pip install dlib --quiet
if errorlevel 1 (
    echo [WARN] dlib auto install failed.
    echo.
    echo Please download dlib manually:
    echo https://github.com/z-mahmud22/Dlib_Windows_Python3.x/releases
    echo Then run:  pip install dlib-19.24.1-cpXX-cpXX-win_amd64.whl
    pause
)

:: Install rest
echo Installing face_recognition, Flask, OpenCV, MySQL connector...
pip install face_recognition Flask opencv-python mysql-connector-python numpy tabulate Pillow --quiet

echo.
echo [3/4] Checking MySQL...
echo.
echo Make sure:
echo   1. MySQL is installed and running
echo   2. You have updated config.py with your MySQL password
echo   3. You have run schema.sql in MySQL
echo.
echo Open config.py and set your password:
echo   "password": "your_mysql_password"
echo.

set /p SKIP="Have you set your MySQL password in config.py? (y/n): "
if /i "%SKIP%"=="n" (
    echo Please edit config.py first, then re-run this script.
    start notepad config.py
    pause
    exit /b
)

echo.
echo [4/4] Starting the web app...
echo.
echo =====================================================
echo   Open your browser: http://localhost:5000
echo =====================================================
echo.

python app.py

pause
