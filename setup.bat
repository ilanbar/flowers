
@echo off
rem if .venv is active deactivate it
if not "%VIRTUAL_ENV%"=="" (
    echo Deactivating virtual environment...
    call deactivate
)

rem if .venv folder exist, remove it
if exist .venv (
    echo Removing existing .venv...
    rmdir /s /q .venv
)

rem create a new virtual environment in .venv folder
echo Creating new virtual environment...
python -m venv .venv

rem activate the virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

rem upgrade pip to the latest version
echo Upgrading pip...
pip install --upgrade pip

rem install required packages
echo Installing requirements...
pip install -r requirements.txt

echo Setup complete!
