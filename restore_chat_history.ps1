# Cursor Chat History Recovery Script
# Run this AFTER closing Cursor completely

Write-Host "Cursor Chat History Recovery Script" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Cursor is running
$cursorProcess = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcess) {
    Write-Host "ERROR: Cursor is still running! Please close Cursor completely and run this script again." -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

$workspaceRoot = "$env:APPDATA\Cursor\User\workspaceStorage"
$newWorkspace = "008b91114f315f38139acb565bf86543"  # Current (empty) - OneDrive path
$oldWorkspace = "9ce298660b83bc717c72454cd1f53ff1"  # Old (has conversations) - Desktop path

Write-Host "Step 1: Backing up current workspace..." -ForegroundColor Yellow
if (Test-Path "$workspaceRoot\$newWorkspace") {
    Rename-Item "$workspaceRoot\$newWorkspace" "${newWorkspace}_backup" -ErrorAction Stop
    Write-Host "  Backed up to ${newWorkspace}_backup" -ForegroundColor Green
} else {
    Write-Host "  Current workspace not found (already moved?)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2: Copying old workspace with your conversations..." -ForegroundColor Yellow
if (Test-Path "$workspaceRoot\$oldWorkspace") {
    Copy-Item "$workspaceRoot\$oldWorkspace" "$workspaceRoot\$newWorkspace" -Recurse -ErrorAction Stop
    Write-Host "  Copied successfully!" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Old workspace not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Updating workspace path reference..." -ForegroundColor Yellow
$wsJsonPath = "$workspaceRoot\$newWorkspace\workspace.json"
$newContent = '{   "folder": "file:///c%3A/Users/simon/OneDrive/Desktop/Quarterback_v1" }'
Set-Content $wsJsonPath $newContent -ErrorAction Stop
Write-Host "  Updated workspace.json" -ForegroundColor Green

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "SUCCESS! Your chat history should be restored." -ForegroundColor Green
Write-Host "You can now open Cursor and check your conversations." -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
