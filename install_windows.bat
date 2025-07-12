@echo off
if exist venv\ (
    echo Venv folder exists
) else (
    @echo Creating virtual environment...
    python -m venv venv
    if exist venv\Scripts\python.exe (
        venv\Scripts\python.exe -m pip install --upgrade pip
        venv\Scripts\pip install -r requirements.txt
    ) else (
        echo Failure creating virtual environment
    )
)

