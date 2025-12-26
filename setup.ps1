# if .venv is active deactivate it
if ($env:VIRTUAL_ENV) {
    Write-Host "Deactivating virtual environment..."
    deactivate
}

# if .venv folder exist, remove it
if (Test-Path .venv) {
    Write-Host "Removing existing .venv..."
    Remove-Item -Path .venv -Recurse -Force
}

# create a new virtual environment in .venv folder
Write-Host "Creating new virtual environment..."
python -m venv .venv

# activate the virtual environment
Write-Host "Activating virtual environment..."
. .venv\Scripts\Activate.ps1

# upgrade pip to the latest version
Write-Host "Upgrading pip..."
pip install --upgrade pip

Write-Host "Installing requirements..."
pip install -r requirements.txt

Write-Host "Setup complete!"