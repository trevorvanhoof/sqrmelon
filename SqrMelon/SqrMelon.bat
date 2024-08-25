@echo off
setlocal enabledelayedexpansion

rem Search for the most recent version of Python 3 in %LOCALAPPDATA%\Programs\Python.
set "PYTHON_DIR=%LOCALAPPDATA%\Programs\Python"
set "LATEST_VERSION=0"
set "LATEST_PYTHON="

for /D %%d in ("%PYTHON_DIR%\Python3*") do (
    set "VERSION=%%~nxd"
    set "VERSION=!VERSION:Python=!"
    if !VERSION! gtr !LATEST_VERSION! (
        set "LATEST_VERSION=!VERSION!"
        set "LATEST_PYTHON=%%d"
    )
)

if "%LATEST_PYTHON%"=="" (
    echo No Python 3 installment found in  %PYTHON_DIR%.
    exit /b 1
)
"%LATEST_PYTHON%\python.exe" main.py %1
