@echo off
REM Build LimitlessTCG Scraper into a standalone .exe
REM Usage: Run this from the project root directory

echo ============================================
echo  LimitlessTCG Scraper - Build EXE
echo ============================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: No .venv found, using system Python
)
echo.

REM Step 1: Run tests
echo Running tests...
python test_scraper.py
if errorlevel 1 (
    echo.
    echo ERROR: Tests failed. Fix issues before building.
    pause
    exit /b 1
)
echo.

REM Step 2: Clean previous build artifacts
echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "LimitlessTCGScraper.spec" del /q "LimitlessTCGScraper.spec"
echo.

REM Step 3: Build the .exe
echo Building standalone .exe with PyInstaller...
python -m PyInstaller --onefile --windowed --name LimitlessTCGScraper --add-data "config.json;." run_gui.py
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)
echo.

REM Step 4: Copy .exe to project root
echo Copying .exe to project root...
copy "dist\LimitlessTCGScraper.exe" "."
if errorlevel 1 (
    echo.
    echo ERROR: Failed to copy .exe to project root.
    pause
    exit /b 1
)
echo.

REM Step 5: Clean up build artifacts (keep dist/ with the .exe)
echo Cleaning up build artifacts...
if exist "build" rmdir /s /q "build"
if exist "LimitlessTCGScraper.spec" del /q "LimitlessTCGScraper.spec"
echo.

echo ============================================
echo  Build complete!
echo  EXE location: LimitlessTCGScraper.exe
echo ============================================
echo.
echo To distribute: Upload LimitlessTCGScraper.exe to a GitHub Release.
pause
