@echo off
REM Training script for Scientisti activities using Claude 3.7 Sonnet model

echo ======================================================
echo   La Serenissima - Scientisti Training with Sonnet
echo ======================================================
echo.
echo This script runs Scientisti activities with Claude 3.7 Sonnet for training.
echo.

REM Set the model to use for training
set MODEL=claude-3-7-sonnet-latest

REM Save current directory and change to backend
pushd %~dp0\..\

REM Check if a username was provided
if "%1"=="" (
    echo Running training for all Scientisti with model: %MODEL%
    python3 scripts\test_scientisti_activities.py --model %MODEL% --activity all
) else (
    echo Running training for %1 with model: %MODEL%
    python3 scripts\test_scientisti_activities.py --username %1 --model %MODEL% --activity all
)

REM Return to original directory
popd

echo.
echo Training session complete!
echo.
echo Note: The --model parameter ensures all KinOS calls use Claude 3.7 Sonnet
echo instead of the default 'local' model for higher quality research outputs.
pause