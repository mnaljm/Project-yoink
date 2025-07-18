@echo off
REM Discord Yoink - Quick Setup Script for Windows
REM This script sets up the Discord Yoink project on Windows

echo Discord Yoink - Setup Script
echo =============================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo Checking Python version...
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"
if errorlevel 1 (
    echo Error: Python 3.8 or higher is required
    python --version
    pause
    exit /b 1
)

echo [OK] Python version check passed

REM Ask about virtual environment
set /p create_venv="Create virtual environment? [y/N]: "
if /i "%create_venv%"=="y" (
    echo Creating virtual environment...
    python -m venv venv
    
    REM Activate virtual environment
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
        echo [OK] Virtual environment created and activated
    ) else (
        echo Warning: Could not activate virtual environment
    )
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed successfully

REM Run setup script
echo Running setup script...
python project_setup.py

echo.
echo Setup complete! You can now use Discord Yoink.
echo.
if exist "venv\Scripts\activate.bat" (
    echo If you created a virtual environment, remember to activate it:
    echo venv\Scripts\activate.bat
    echo.
)
pause
