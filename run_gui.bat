@echo off
REM LimitlessTCG Scraper GUI Launcher for Windows
REM This batch file provides an easy way to launch the GUI application

echo Starting LimitlessTCG Scraper GUI...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://python.org
    pause
    exit /b 1
)

REM Try to run the GUI
python run_gui.py

REM If there was an error, pause to show the message
if errorlevel 1 (
    echo.
    echo An error occurred. Please check the message above.
    pause
)
