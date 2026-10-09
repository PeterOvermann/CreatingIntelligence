@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PATH=%USERPROFILE%\.ci"

rem Prefer the py launcher and ask it for a 64-bit Python 3 explicitly;
rem fall back to whatever "python" is on PATH.
where py >nul 2>nul
if errorlevel 1 (
    set "PY=python"
) else (
    set "PY=py -3-64"
)

rem The memory backend requires a 64-bit Python; stop before creating anything.
%PY% -c "import struct, sys; sys.exit(struct.calcsize('P') * 8 != 64)" >nul 2>nul
if errorlevel 1 (
    echo ERROR: creating-intelligence requires a 64-bit Python 3, but none was found.
    echo Install it from https://www.python.org/downloads/windows/ and rerun this script.
    exit /b 1
)

where dot >nul 2>nul
if errorlevel 1 (
    echo ============================================================
    echo WARNING: Graphviz ^('dot'^) was not found.
    echo Circuit diagrams will use a fallback layout instead of the
    echo left-to-right layout. Everything else works normally.
    echo To enable the left-to-right layout, install Graphviz:
    echo   winget install Graphviz.Graphviz
    echo ============================================================
)

rem Create virtual environment if not present
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Creating virtual environment at "%VENV_PATH%"...
    %PY% -m venv "%VENV_PATH%" || goto :fail
)

call "%VENV_PATH%\Scripts\activate.bat" || goto :fail

echo Installing creating-intelligence package...
python -m pip install -q --upgrade pip || goto :fail
python -m pip install -q -e "%SCRIPT_DIR%.[viz]" || goto :fail

rem A failed C compile no longer stops the install, so check which backend loads.
set "MEMORY_BACKEND="
set "CI_BACKEND="
for /f "delims=" %%b in ('python -W ignore -c "import creating_intelligence as ci; print(ci.backend)"') do set "CI_BACKEND=%%b"

if /i not "%CI_BACKEND%"=="c_ffi" (
    echo ============================================================
    echo WARNING: The C memory backend could not be built.
    echo creating-intelligence works, but uses the slower pure-Python backend.
    echo To get the fast C backend, install the Visual Studio Build Tools
    echo with the "Desktop development with C++" workload, then rerun this script:
    echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo ============================================================
)

echo Setup complete ^(memory backend: %CI_BACKEND%^). Activate with: "%VENV_PATH%\Scripts\activate.bat"
exit /b 0

:fail
echo ERROR: Setup failed. See the messages above.
exit /b 1
