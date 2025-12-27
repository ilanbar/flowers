# Build the executable
& "C:/Program Files/Python314/python.exe" -m PyInstaller --noconfirm --onefile --windowed --name "FlowerShopManager" main.py

# Ensure dist directory exists (it should after build)
if (Test-Path dist) {
    # Copy data files to dist so the exe can run
    Copy-Item "Flowers.json" -Destination "dist" -Force
    Copy-Item "Colors.json" -Destination "dist" -Force
    Copy-Item "Bouquets.json" -Destination "dist" -Force
    if (Test-Path "DefaultPricing.json") {
        Copy-Item "DefaultPricing.json" -Destination "dist" -Force
    }
    
    # Create necessary directories
    New-Item -ItemType Directory -Force -Path "dist\orders"
    New-Item -ItemType Directory -Force -Path "dist\backups"
    
    Write-Host "Build complete. Executable is in 'dist\FlowerShopManager.exe'"
}
