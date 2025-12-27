# Determine Python executable
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonExe = ".\.venv\Scripts\python.exe"
} else {
    $pythonExe = "python"
}

# Build the executable
# We use --add-data to bundle the Excel files inside the exe.
# Format for Windows is "source;dest". "." means root of the bundle.
# $add_data = "--add-data 'Flowers.xlsx;.' --add-data 'Colors.xlsx;.' --add-data 'Bouquets.xlsx;.' --add-data 'DefaultPricing.xlsx;.'"

# Note: We invoke PyInstaller via cmd /c to handle the quoting of arguments correctly if needed, 
# but passing them directly to the python command usually works if quoted properly.
# However, PowerShell parsing of quotes can be tricky.
# Let's construct the command string.

& $pythonExe -m PyInstaller --noconfirm --onefile --windowed --name "FlowerShopManager" main.py

# Ensure dist directory exists (it should after build)
if (Test-Path dist) {
    # Copy data files to dist so the exe can run
    # We explicitly copy the Excel files needed for the application
    $files = @("Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx")
    foreach ($file in $files) {
        if (Test-Path $file) {
            Copy-Item $file -Destination "dist" -Force
        }
    }

    # Copy credentials.json for Google Drive Sync
    if (Test-Path "credentials.json") {
        Copy-Item "credentials.json" -Destination "dist" -Force
        Write-Host "Copied credentials.json to dist."
    } else {
        Write-Warning "credentials.json not found! Google Drive Sync will not work in the built executable."
    }
    
    # Also copy legacy JSON files if they exist, just in case
    # Exclude token.json (session data) and credentials.json (already handled)
    Get-ChildItem -Path . -Filter "*.json" | Where-Object { $_.Name -ne "token.json" -and $_.Name -ne "credentials.json" } | Copy-Item -Destination "dist" -Force
    
    # Create necessary directories
    New-Item -ItemType Directory -Force -Path "dist\orders"
    New-Item -ItemType Directory -Force -Path "dist\backups"
    
    Write-Host "Build complete. Executable is in 'dist\FlowerShopManager.exe'"
}
