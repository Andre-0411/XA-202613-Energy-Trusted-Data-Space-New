# ============================================================
#  Diagnostic Script - Run this to see actual errors
#  Run as Administrator in PowerShell
# ============================================================

$ErrorActionPreference = "Continue"
$PROJECT_DIR = "D:\Andre\project\energy-trusted-data-space"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTIC: Frontend Build" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

Set-Location "$PROJECT_DIR\frontend"

Write-Host ""
Write-Host "--- Step 1: TypeScript Check (tsc -b) ---" -ForegroundColor Yellow
$tscOutput = & npx tsc -b 2>&1
$tscExit = $LASTEXITCODE
Write-Host $tscOutput
if ($tscExit -eq 0) {
    Write-Host "[OK] TypeScript check passed" -ForegroundColor Green
} else {
    Write-Host "[FAIL] TypeScript check failed (exit code: $tscExit)" -ForegroundColor Red
    Write-Host ""
    Write-Host "TypeScript errors found above. These need to be fixed." -ForegroundColor Yellow
}

if ($tscExit -eq 0) {
    Write-Host ""
    Write-Host "--- Step 2: Vite Build ---" -ForegroundColor Yellow
    $viteOutput = & npx vite build 2>&1
    $viteExit = $LASTEXITCODE
    Write-Host $viteOutput
    if ($viteExit -eq 0) {
        Write-Host "[OK] Vite build passed" -ForegroundColor Green
        if (Test-Path "dist\index.html") {
            Write-Host "[OK] dist/index.html exists" -ForegroundColor Green
        }
    } else {
        Write-Host "[FAIL] Vite build failed (exit code: $viteExit)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTIC: Backend Startup" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

Set-Location "$PROJECT_DIR\backend"

Write-Host ""
Write-Host "--- Step 3: Python Import Check ---" -ForegroundColor Yellow
$importCheck = & python -c "from app.main import app; print('[OK] app.main imports successfully')" 2>&1
$importExit = $LASTEXITCODE
Write-Host $importCheck
if ($importExit -ne 0) {
    Write-Host "[FAIL] Import error detected" -ForegroundColor Red
}

Write-Host ""
Write-Host "--- Step 4: Uvicorn Test Start (5 second test) ---" -ForegroundColor Yellow
Write-Host "Starting uvicorn, will check port 8000 after 5 seconds..."
$uvicornProc = Start-Process python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5

$portCheck = netstat -ano | Select-String ":8000.*LISTENING"
if ($portCheck) {
    Write-Host "[OK] Backend is listening on port 8000" -ForegroundColor Green
    # Try health check
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "[OK] Health check response: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Health check request failed: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[FAIL] Backend NOT listening on port 8000" -ForegroundColor Red
    Write-Host "Process may have crashed. Check if python process is still running:" -ForegroundColor Yellow
    Get-Process -Name python -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, StartTime -AutoSize
}

Write-Host ""
Write-Host "--- Step 5: Check running processes ---" -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, StartTime, @{Name="CommandLine";Expression={$_.CommandLine}} -AutoSize -Wrap

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTIC COMPLETE" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Copy ALL the output above and send it to me." -ForegroundColor White
Write-Host "I will analyze the errors and provide fixes." -ForegroundColor White

pause
