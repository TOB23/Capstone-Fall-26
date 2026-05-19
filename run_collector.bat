@echo off
REM ====================================================================
REM  run_collector.bat - run ONE outage collection pass on Windows.
REM
REM  Task Scheduler runs this file on a schedule. It activates the project
REM  Python environment, runs one pass of collector.py, and appends the
REM  result to a dated log so missed or failed passes are visible.
REM
REM  SETUP - edit the two paths below to match your machine, then save:
REM    REPO_DIR  : the folder containing collector.py
REM    PYTHON    : full path to the python.exe of your project environment
REM  Find PYTHON by activating your env and running:  where python
REM ====================================================================

set "REPO_DIR=C:\Users\YOURNAME\outage-verification"
set "PYTHON=C:\Users\YOURNAME\miniconda3\envs\capstone\python.exe"

REM --- do not edit below this line --------------------------------------
set "LOGDIR=%REPO_DIR%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM One log file per day: collector_YYYY-MM-DD.log
for /f "tokens=1-3 delims=/- " %%a in ('echo %DATE%') do set "TODAY=%%c-%%b-%%a"
set "LOGFILE=%LOGDIR%\collector_%TODAY%.log"

echo. >> "%LOGFILE%"
echo ==== pass started %DATE% %TIME% ==== >> "%LOGFILE%"

cd /d "%REPO_DIR%"
if errorlevel 1 (
    echo ERROR: could not cd to REPO_DIR - check the path. >> "%LOGFILE%"
    exit /b 1
)

"%PYTHON%" collector.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
    echo ==== pass finished OK %DATE% %TIME% ==== >> "%LOGFILE%"
) else (
    echo ==== pass FAILED rc=%RC% %DATE% %TIME% ==== >> "%LOGFILE%"
)
exit /b %RC%
