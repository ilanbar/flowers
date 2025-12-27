# Check if Python is available
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "Found Python: $pythonVersion"
} catch {
    Write-Error "Python is not found in PATH. Please install Python 3.x and add it to PATH."
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & python -m venv .venv
} else {
    Write-Host "Virtual environment already exists."
}

# Define path to pip in the virtual environment
$pipPath = ".\.venv\Scripts\pip.exe"

if (-not (Test-Path $pipPath)) {
    # Fallback for non-Windows or different structure, though this is a ps1 script
    $pipPath = ".\.venv\bin\pip"
}

# Upgrade pip
Write-Host "Upgrading pip..."
& $pipPath install --upgrade pip

# Install requirements
if (Test-Path "requirements.txt") {
    Write-Host "Installing dependencies from requirements.txt..."
    & $pipPath install -r requirements.txt
} else {
    Write-Warning "requirements.txt not found. Skipping dependency installation."
}

Write-Host "Setup complete. To activate the environment, run: .\.venv\Scripts\Activate.ps1"
