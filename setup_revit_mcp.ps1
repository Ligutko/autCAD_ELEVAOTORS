# ============================================================================
# REVIT MCP SETUP - Automatic Installation
# ============================================================================
# This script automatically configures Revit MCP System
#
# Usage: (PowerShell as Administrator)
#   cd "D:\autocad project"
#   .\setup_revit_mcp.ps1
#
# Author: Claude Code
# Date: 2026-01-01
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  REVIT MCP SYSTEM - AUTOMATIC SETUP" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"

# ============================================================================
# Step 1: Check Revit
# ============================================================================

Write-Host "[1/5] Checking Revit..." -ForegroundColor Yellow

$revitPath = "C:\Program Files\Autodesk\Revit 2026\Revit.exe"

if (Test-Path $revitPath) {
    Write-Host "  OK Revit 2026 found: $revitPath" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Revit 2026 not found!" -ForegroundColor Red
    Write-Host "  Install Revit from https://www.autodesk.com/" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# Step 2: Install pyRevit (if needed)
# ============================================================================

Write-Host ""
Write-Host "[2/5] Checking pyRevit..." -ForegroundColor Yellow

$pyrevitPath = "$env:APPDATA\pyRevit"

if (Test-Path $pyrevitPath) {
    Write-Host "  OK pyRevit already installed: $pyrevitPath" -ForegroundColor Green
} else {
    Write-Host "  WARNING: pyRevit not found. Downloading..." -ForegroundColor Yellow

    # Download installer
    $installerUrl = "https://github.com/pyrevitlabs/pyRevit/releases/download/v4.8.16.24143/pyRevit_4.8.16.24143_signed.exe"
    $installerPath = "$env:TEMP\pyrevit_installer.exe"

    Write-Host "  Downloading pyRevit installer..." -ForegroundColor Yellow

    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "  OK Downloaded: $installerPath" -ForegroundColor Green

        Write-Host ""
        Write-Host "  WARNING: Run installer manually!" -ForegroundColor Yellow
        Write-Host "  1. Open: $installerPath" -ForegroundColor Cyan
        Write-Host "  2. Select Revit 2026" -ForegroundColor Cyan
        Write-Host "  3. Click Install" -ForegroundColor Cyan
        Write-Host "  4. After installation press Enter here..." -ForegroundColor Cyan

        # Open installer
        Start-Process $installerPath

        # Wait for confirmation
        Read-Host '  Press Enter after installing pyRevit'

    } catch {
        Write-Host "  ERROR: Failed to download installer" -ForegroundColor Red
        Write-Host "  Download manually: https://github.com/pyrevitlabs/pyRevit/releases" -ForegroundColor Yellow
        exit 1
    }
}

# ============================================================================
# Step 3: Configure pyRevit Extension (Listener)
# ============================================================================

Write-Host ""
Write-Host "[3/5] Configuring pyRevit Extension..." -ForegroundColor Yellow

$extensionPath = "$env:APPDATA\pyRevit\Extensions\RevitMCP.extension\RevitMCP.tab\Listener.panel\StartListener.pushbutton"

# Create folder structure
Write-Host "  Creating folders..." -ForegroundColor Yellow
New-Item -Path $extensionPath -ItemType Directory -Force | Out-Null

# Copy listener script
$sourceScript = "D:\autocad project\revit-mcp\pyrevit_extension\revit_listener.py"
$targetScript = "$extensionPath\script.py"

if (Test-Path $sourceScript) {
    Write-Host "  Copying listener script..." -ForegroundColor Yellow
    Copy-Item $sourceScript $targetScript -Force
    Write-Host "  OK Listener script installed: $targetScript" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Listener script not found: $sourceScript" -ForegroundColor Red
    exit 1
}

# Create icon (optional)
$iconContent = @"
# RevitMCP Listener Icon
# Auto-generated
"@
Set-Content -Path "$extensionPath\bundle.yaml" -Value $iconContent

Write-Host "  OK pyRevit Extension configured" -ForegroundColor Green

# ============================================================================
# Step 4: Create queue folders
# ============================================================================

Write-Host ""
Write-Host "[4/5] Creating MCP Server folders..." -ForegroundColor Yellow

$commandsQueue = "D:\autocad project\revit-mcp\commands_queue"
$resultsQueue = "D:\autocad project\revit-mcp\results_queue"
$familiesDir = "D:\autocad project\revit-mcp\families"

New-Item -Path $commandsQueue -ItemType Directory -Force | Out-Null
New-Item -Path $resultsQueue -ItemType Directory -Force | Out-Null
New-Item -Path $familiesDir -ItemType Directory -Force | Out-Null

Write-Host "  OK Commands Queue: $commandsQueue" -ForegroundColor Green
Write-Host "  OK Results Queue: $resultsQueue" -ForegroundColor Green
Write-Host "  OK Families Dir: $familiesDir" -ForegroundColor Green

# ============================================================================
# Step 5: Check Python dependencies
# ============================================================================

Write-Host ""
Write-Host "[5/5] Checking Python dependencies..." -ForegroundColor Yellow

$requirementsFile = "D:\autocad project\revit-mcp\requirements.txt"

if (Test-Path $requirementsFile) {
    Write-Host "  Installing dependencies..." -ForegroundColor Yellow

    try {
        Set-Location "D:\autocad project\revit-mcp"
        pip install -r requirements.txt --quiet
        Write-Host "  OK Python dependencies installed" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING: Failed to install dependencies" -ForegroundColor Yellow
        Write-Host "  Run manually: pip install -r requirements.txt" -ForegroundColor Cyan
    }
} else {
    Write-Host "  WARNING: requirements.txt not found" -ForegroundColor Yellow
}

# ============================================================================
# COMPLETION
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open Revit 2026" -ForegroundColor Cyan
Write-Host "2. Check pyRevit tab in interface" -ForegroundColor Cyan
Write-Host "3. Click Start Listener button" -ForegroundColor Cyan
Write-Host "4. Create new project: File -> New -> Project" -ForegroundColor Cyan
Write-Host "5. Save as: D:\autocad project\Test_Grain_Elevator.rvt" -ForegroundColor Cyan
Write-Host ""
Write-Host "TEST CONNECTION:" -ForegroundColor Yellow
Write-Host "  cd D:\autocad project\revit-mcp" -ForegroundColor Cyan
Write-Host "  python test_mcp_connection.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Detailed instructions: D:\autocad project\QUICK_START.md" -ForegroundColor Green
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host 'Press Enter to finish'
