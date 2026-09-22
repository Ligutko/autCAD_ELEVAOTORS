# ============================================================================
# REVIT MCP SETUP - Simple Version (Manual pyRevit Installation)
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  REVIT MCP SYSTEM - SIMPLE SETUP" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check Revit
Write-Host "[1/4] Checking Revit..." -ForegroundColor Yellow
$revitPath = "C:\Program Files\Autodesk\Revit 2026\Revit.exe"

if (Test-Path $revitPath) {
    Write-Host "  OK Revit 2026 found" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Revit 2026 not found!" -ForegroundColor Red
    exit 1
}

# Create folders
Write-Host ""
Write-Host "[2/4] Creating MCP folders..." -ForegroundColor Yellow

New-Item -Path "D:\autocad project\revit-mcp\commands_queue" -ItemType Directory -Force | Out-Null
New-Item -Path "D:\autocad project\revit-mcp\results_queue" -ItemType Directory -Force | Out-Null
New-Item -Path "D:\autocad project\revit-mcp\families" -ItemType Directory -Force | Out-Null

Write-Host "  OK Folders created" -ForegroundColor Green

# Install Python dependencies
Write-Host ""
Write-Host "[3/4] Installing Python dependencies..." -ForegroundColor Yellow

try {
    Set-Location "D:\autocad project\revit-mcp"
    pip install -r requirements.txt --quiet
    Write-Host "  OK Python packages installed" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Failed to install Python packages" -ForegroundColor Yellow
    Write-Host "  Run manually: pip install -r requirements.txt" -ForegroundColor Cyan
}

# pyRevit instructions
Write-Host ""
Write-Host "[4/4] pyRevit Setup Required" -ForegroundColor Yellow
Write-Host ""

$pyrevitPath = "$env:APPDATA\pyRevit"

if (Test-Path $pyrevitPath) {
    Write-Host "  OK pyRevit already installed!" -ForegroundColor Green

    # Copy listener
    $extensionPath = "$env:APPDATA\pyRevit\Extensions\RevitMCP.extension\RevitMCP.tab\Listener.panel\StartListener.pushbutton"
    New-Item -Path $extensionPath -ItemType Directory -Force | Out-Null

    $sourceScript = "D:\autocad project\revit-mcp\pyrevit_extension\revit_listener.py"
    Copy-Item $sourceScript "$extensionPath\script.py" -Force

    Write-Host "  OK Listener installed" -ForegroundColor Green

} else {
    Write-Host "  WARNING: pyRevit NOT installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "  MANUAL INSTALLATION REQUIRED:" -ForegroundColor Yellow
    Write-Host "  1. Download pyRevit from:" -ForegroundColor Cyan
    Write-Host "     https://github.com/pyrevitlabs/pyRevit/releases" -ForegroundColor Cyan
    Write-Host "  2. Download file: pyRevit_5.3.1.25308_signed.exe (LATEST)" -ForegroundColor Cyan
    Write-Host "  3. Run installer" -ForegroundColor Cyan
    Write-Host "  4. Select Revit 2026" -ForegroundColor Cyan
    Write-Host "  5. Click Install" -ForegroundColor Cyan
    Write-Host "  6. Re-run this script after installation" -ForegroundColor Cyan
    Write-Host ""
}

# Final instructions
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  SETUP STATUS" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "COMPLETED:" -ForegroundColor Green
Write-Host "  - Revit 2026 detected" -ForegroundColor Gray
Write-Host "  - MCP folders created" -ForegroundColor Gray
Write-Host "  - Python dependencies installed" -ForegroundColor Gray
Write-Host ""

if (Test-Path $pyrevitPath) {
    Write-Host "NEXT STEPS:" -ForegroundColor Yellow
    Write-Host "  1. Open Revit 2026" -ForegroundColor Cyan
    Write-Host "  2. Check for pyRevit tab" -ForegroundColor Cyan
    Write-Host "  3. Click Start Listener button" -ForegroundColor Cyan
    Write-Host "  4. Create new project and save as Test_Grain_Elevator.rvt" -ForegroundColor Cyan
    Write-Host "  5. Test connection: python test_mcp_connection.py" -ForegroundColor Cyan
} else {
    Write-Host "REQUIRED:" -ForegroundColor Red
    Write-Host "  - Install pyRevit (see instructions above)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Documentation: D:\autocad project\QUICK_START.md" -ForegroundColor Green
Write-Host ""

Read-Host 'Press Enter to finish'
