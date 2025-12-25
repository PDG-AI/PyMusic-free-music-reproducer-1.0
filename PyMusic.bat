@echo off

REM ===== CONFIG =====
set VENV_DIR=venv
set SCRIPT=main.py
set REQ=requirements.txt
REM ==================

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] venv not found, creating one
    python -m venv %VENV_DIR%
)

call %VENV_DIR%\Scripts\activate.bat

python -m pip install --upgrade pip

if exist "%REQ%" (
    echo downloading dependencies
    pip install -r %REQ%
) else (
    echo [WARN] requirements file not found, skipping
)

python %SCRIPT%

pause
