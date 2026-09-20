@echo off
setlocal

where dot >nul 2>nul
if %errorlevel% neq 0 (
    echo ============================================================
    echo WARNING: Graphviz ^('dot'^) is required for advanced circuit schematics but was not found.
    echo The package will install normally, but visualization features will use a fallback layout.
    echo Please install Graphviz manually if needed:
    echo   winget install Graphviz.Graphviz
    echo ============================================================
)

set "SCRIPT_DIR=%~dp0"
set "VENV_PATH=%USERPROFILE%\.ci"

rem Create virtual environment if not present
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Creating virtual environment at %VENV_PATH%...
    python -m venv "%VENV_PATH%"
)

call "%VENV_PATH%\Scripts\activate.bat"

echo Installing creating-intelligence package...
python -m pip install -q --upgrade pip
pip install -q -e "%SCRIPT_DIR%."

echo Setup complete. Activate with: "%VENV_PATH%\Scripts\activate.bat"