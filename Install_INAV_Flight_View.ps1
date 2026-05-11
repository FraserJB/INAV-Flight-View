# INAV Flight View - Standard Installer (PowerShell)
# This script sets up a virtual environment and creates a Desktop shortcut.

$AppDir = $PSScriptRoot
$VenvDir = Join-Path $AppDir "venv"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "INAV Flight View.lnk"
$RequirementsFile = Join-Path $AppDir "requirements.txt"
$MainScript = Join-Path $AppDir "main.py"

Write-Host "--- INAV Flight View Installer ---" -ForegroundColor Cyan

# 1. Check for Python
Write-Host "Checking for Python..." -NoNewline
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Python not found" }
    Write-Host " Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "`nPython is NOT installed on this machine." -ForegroundColor Yellow
    Write-Host "Please download and install Python 3.12 (or 3.10+) from:"
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Blue
    Write-Host "`n*** IMPORTANT: Check the box 'Add Python to PATH' during installation! ***" -ForegroundColor White -BackgroundColor Red
    Start-Process "https://www.python.org/downloads/"
    Read-Host "`nPress Enter once Python is installed and you've restarted your terminal..."
    exit
}

# 2. Create Virtual Environment
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating Virtual Environment (this may take a minute)..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create Virtual Environment." -ForegroundColor Red
        exit
    }
}

# 3. Install Dependencies
Write-Host "Installing/Updating dependencies..."
$pip = Join-Path $VenvDir "Scripts\pip.exe"
& $pip install -r $RequirementsFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies." -ForegroundColor Red
    exit
}

# 4. Create Desktop Shortcut
Write-Host "Creating Desktop Shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $VenvDir "Scripts\pythonw.exe"
$Shortcut.Arguments = "`"$MainScript`""
$Shortcut.WorkingDirectory = $AppDir
$Shortcut.Description = "INAV Flight View - 3D Log Viewer"
# Note: You can add an icon path here if you have an .ico file
# $Shortcut.IconLocation = Join-Path $AppDir "icon.ico"
$Shortcut.Save()

Write-Host "`n--- INSTALLATION COMPLETE ---" -ForegroundColor Green
Write-Host "You can now launch the app from the 'INAV Flight View' shortcut on your Desktop."
Read-Host "Press Enter to exit..."
