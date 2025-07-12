@echo off
@echo Updating virtual environment...
if exist venv\Scripts\python.exe (
    venv\Scripts\pip install --no-deps -r requirements.txt
) else (
    echo Failure updating virtual environment
)
