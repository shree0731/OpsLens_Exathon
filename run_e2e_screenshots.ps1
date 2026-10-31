$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host " OpsLens Frontend E2E Screenshot & Verification Runner"
Write-Host "============================================================"

# 1. Start Backend FastAPI on 127.0.0.1:8000
Write-Host ">> Starting FastAPI backend on http://127.0.0.1:8000 ..."
$backend = Start-Process "python" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" -PassThru

# 2. Start Vite Preview Server on http://localhost:5173
Write-Host ">> Starting Vite preview server on http://localhost:5173 ..."
$frontend = Start-Process "cmd.exe" -ArgumentList "/c npm run preview -- --port 5173 --host 127.0.0.1" -WorkingDirectory "frontend" -PassThru

try {
    Write-Host ">> Waiting for backend and frontend ports to be ready..."
    $backendReady = $false
    $frontendReady = $false

    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        if (-not $backendReady) {
            $tcp8000 = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue
            if ($tcp8000.TcpTestSucceeded) {
                Write-Host "  -> Backend port 8000 is ready!"
                $backendReady = $true
            }
        }
        if (-not $frontendReady) {
            $tcp5173 = Test-NetConnection -ComputerName 127.0.0.1 -Port 5173 -WarningAction SilentlyContinue
            if ($tcp5173.TcpTestSucceeded) {
                Write-Host "  -> Frontend port 5173 is ready!"
                $frontendReady = $true
            }
        }
        if ($backendReady -and $frontendReady) {
            break
        }
    }

    if (-not $backendReady -or -not $frontendReady) {
        throw "Failed to start servers within timeout. Backend: $backendReady, Frontend: $frontendReady"
    }

    # Run the puppeteer capture script
    Write-Host ">> Running Puppeteer headless Chrome test suite..."
    node frontend/scripts/capture_screenshots.cjs

    Write-Host ">> [SUCCESS] All screenshots captured successfully!"
}
finally {
    Write-Host ">> Stopping background processes..."
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
    if ($frontend -and -not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id -Force
    }
}
