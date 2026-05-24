# ============================================================
#  Energy Trusted Data Space - Windows Deployment Script
#  Server: 10.241.2.64 | No Chocolatey Required
#  Run as Administrator in PowerShell
# ============================================================

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$PASSWORD = "Andre0411"

# ========== Path Config ==========
$SOFTWARE_DIR  = "D:\Andre\software"
$DATA_DIR      = "D:\Andre\data"
$PROJECT_DIR   = "D:\Andre\project\energy-trusted-data-space"
$GITHUB_REPO   = "https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New.git"
$DOWNLOAD_DIR  = "$DATA_DIR\downloads"

$PG_DATA       = "$DATA_DIR\postgresql"
$REDIS_DATA    = "$DATA_DIR\redis"
$NODE_DIR      = "$SOFTWARE_DIR\nodejs"
$REDIS_DIR     = "$SOFTWARE_DIR\redis"
$PG_DIR        = "$SOFTWARE_DIR\postgresql"

function Write-Step($msg) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Yellow
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop; return $true }
    catch { return $false }
}

function Refresh-Path {
    $m = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $u = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$m;$u"
}

function Add-ToPath($newPath) {
    $current = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($current -notlike "*$newPath*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$current;$newPath", "Machine")
        $env:Path = "$env:Path;$newPath"
    }
}

function Download-File($url, $dest) {
    if (Test-Path $dest) {
        Write-Host "    Already downloaded: $dest" -ForegroundColor Gray
        return
    }
    Write-Host "    Downloading: $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
        Write-Host "    Saved: $dest" -ForegroundColor Gray
    } catch {
        Write-Host "    [ERROR] Download failed: $_" -ForegroundColor Red
        throw
    }
}

# ============================================================
#  Step 0: Check Admin + Create Dirs
# ============================================================
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Please run as Administrator!" -ForegroundColor Red
    pause
    exit 1
}

Write-Step "Step 0/8: Create Directory Structure"

$dirs = @($SOFTWARE_DIR, $DATA_DIR, $DOWNLOAD_DIR, $PROJECT_DIR, $PG_DATA, $REDIS_DATA, $NODE_DIR, $REDIS_DIR, $PG_DIR, "$DATA_DIR\logs")
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "  [CREATE] $d" -ForegroundColor Gray
    }
}
Write-Host "  [OK] Directories ready" -ForegroundColor Green

# ============================================================
#  Step 1: Install Node.js (direct download)
# ============================================================
Write-Step "Step 1/8: Install Node.js LTS"

Refresh-Path
if (Test-Command "node") {
    Write-Host "  [SKIP] Node $(node -v) already installed" -ForegroundColor Gray
} else {
    $nodeUrl = "https://nodejs.org/dist/v22.16.0/node-v22.16.0-x64.msi"
    $nodeMsi = "$DOWNLOAD_DIR\node-v22.16.0-x64.msi"

    Download-File $nodeUrl $nodeMsi

    Write-Host "  Installing Node.js to $NODE_DIR..."
    $msiArgs = "/i `"$nodeMsi`" INSTALLDIR=`"$NODE_DIR`" /qn /norestart"
    Start-Process msiexec.exe -ArgumentList $msiArgs -Wait -NoNewWindow

    Add-ToPath $NODE_DIR
    Refresh-Path

    if (Test-Command "node") {
        Write-Host "  [OK] Node $(node -v) installed" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Node install may need PATH refresh. Trying portable..." -ForegroundColor Yellow
        # Fallback: portable zip
        $nodeZip = "$DOWNLOAD_DIR\node-v22.16.0-win-x64.zip"
        $nodeZipUrl = "https://nodejs.org/dist/v22.16.0/node-v22.16.0-win-x64.zip"
        Download-File $nodeZipUrl $nodeZip
        Expand-Archive -Path $nodeZip -DestinationPath $SOFTWARE_DIR -Force
        $extracted = "$SOFTWARE_DIR\node-v22.16.0-win-x64"
        if (Test-Path $extracted) {
            Rename-Item $extracted $NODE_DIR -ErrorAction SilentlyContinue
        }
        Add-ToPath $NODE_DIR
        Refresh-Path
    }
}

Write-Host "  npm: $(npm -v 2>$null)" -ForegroundColor Gray

# ============================================================
#  Step 2: Install PostgreSQL (direct download)
# ============================================================
Write-Step "Step 2/8: Install PostgreSQL"

Refresh-Path
if (Test-Command "psql") {
    Write-Host "  [SKIP] PostgreSQL already installed" -ForegroundColor Gray
} else {
    # Try multiple PostgreSQL download sources
    $pgZip = "$DOWNLOAD_DIR\postgresql-16-win-x64.zip"
    $pgUrls = @(
        "https://get.enterprisedb.com/postgresql/postgresql-16.9-1-windows-x64-binaries.zip",
        "https://get.enterprisedb.com/postgresql/postgresql-16.8-1-windows-x64-binaries.zip",
        "https://get.enterprisedb.com/postgresql/postgresql-16.7-1-windows-x64-binaries.zip"
    )

    Write-Host "  Downloading PostgreSQL 16 binaries..."
    $downloaded = $false
    foreach ($pgUrl in $pgUrls) {
        try {
            Download-File $pgUrl $pgZip
            $downloaded = $true
            break
        } catch {
            Write-Host "    [WARN] URL failed, trying next..." -ForegroundColor Yellow
        }
    }
    if (-not $downloaded) {
        Write-Host "  [ERROR] All PostgreSQL download URLs failed!" -ForegroundColor Red
        Write-Host "  [HINT] Please download PostgreSQL manually from:" -ForegroundColor Yellow
        Write-Host "         https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
        Write-Host "         Extract to: $PG_DIR" -ForegroundColor Yellow
    }

    Write-Host "  Extracting to $PG_DIR..."
    Expand-Archive -Path $pgZip -DestinationPath $PG_DIR -Force

    # Find the extracted subdirectory
    $pgBin = Get-ChildItem $PG_DIR -Directory | Where-Object { $_.Name -like "pgsql" } | Select-Object -First 1
    if (-not $pgBin) {
        $pgBin = Get-ChildItem $PG_DIR -Directory | Select-Object -First 1
    }
    if ($pgBin) {
        $pgBinPath = Join-Path $pgBin.FullName "bin"
        Add-ToPath $pgBinPath
        Refresh-Path
        Write-Host "  [OK] PostgreSQL binaries at: $pgBinPath" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Could not find PostgreSQL bin directory" -ForegroundColor Red
    }
}

# Init PostgreSQL data directory if needed
$pgBinPath = ""
$pgSearch = Get-ChildItem $PG_DIR -Recurse -Filter "psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgSearch) {
    $pgBinPath = Split-Path $pgSearch.FullName
}

if ($pgBinPath -and -not (Test-Path "$PG_DATA\postgresql.conf")) {
    Write-Host "  Initializing PostgreSQL data directory..."
    $initdb = Join-Path $pgBinPath "initdb.exe"
    if (Test-Path $initdb) {
        # Write password to temp file for initdb --pwfile
        $pwFile = Join-Path $DOWNLOAD_DIR "pg_pw.txt"
        $PASSWORD | Out-File -FilePath $pwFile -Encoding ascii -NoNewline
        & $initdb -D $PG_DATA -U postgres -E UTF8 --locale=C -A md5 --pwfile="$pwFile" 2>&1 | Out-Null
        Remove-Item $pwFile -ErrorAction SilentlyContinue
        Write-Host "  [OK] PostgreSQL data initialized" -ForegroundColor Green
    }
}

# Start PostgreSQL
if ($pgBinPath) {
    $pgCtl = Join-Path $pgBinPath "pg_ctl.exe"
    $psql = Join-Path $pgBinPath "psql.exe"
    if (Test-Path $pgCtl) {
        # Check if already running
        $pgRunning = netstat -ano | Select-String ":5432.*LISTENING"
        if (-not $pgRunning) {
            Write-Host "  Starting PostgreSQL..."
            & $pgCtl start -D $PG_DATA -l "$DATA_DIR\logs\postgresql.log" -w 2>&1 | Out-Null

            # Wait for PostgreSQL to be ready (max 15 seconds)
            $waitCount = 0
            while ($waitCount -lt 15) {
                Start-Sleep -Seconds 1
                $waitCount++
                $pgRunning = netstat -ano | Select-String ":5432.*LISTENING"
                if ($pgRunning) { break }
                Write-Host "    Waiting for PostgreSQL... ($waitCount s)" -ForegroundColor Gray
            }
        }

        if (netstat -ano | Select-String ":5432.*LISTENING") {
            Write-Host "  [OK] PostgreSQL is running on port 5432" -ForegroundColor Green

            # Create database
            $env:PGPASSWORD = $PASSWORD
            $result = & $psql -U postgres -h localhost -c "CREATE DATABASE energy_tds;" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Database energy_tds created" -ForegroundColor Green
            } else {
                Write-Host "  [INFO] Database may already exist" -ForegroundColor Gray
            }
        } else {
            Write-Host "  [ERROR] PostgreSQL failed to start! Check log: $DATA_DIR\logs\postgresql.log" -ForegroundColor Red
        }
    }
}

# ============================================================
#  Step 3: Install Redis (direct download)
# ============================================================
Write-Step "Step 3/8: Install Redis"

Refresh-Path
if (Test-Command "redis-server") {
    Write-Host "  [SKIP] Redis already installed" -ForegroundColor Gray
} else {
    $redisUrl = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
    $redisZip = "$DOWNLOAD_DIR\redis-x64-5.0.14.1.zip"

    Write-Host "  Downloading Redis..."
    Download-File $redisUrl $redisZip

    Write-Host "  Extracting to $REDIS_DIR..."
    Expand-Archive -Path $redisZip -DestinationPath $REDIS_DIR -Force

    Add-ToPath $REDIS_DIR
    Refresh-Path
    Write-Host "  [OK] Redis extracted to $REDIS_DIR" -ForegroundColor Green
}

# Configure Redis
$redisConf = @"
dir $REDIS_DATA
appendonly yes
appendfilename "appendonly.aof"
dbfilename dump.rdb
maxmemory 256mb
maxmemory-policy allkeys-lru
"@
$redisConfPath = "$REDIS_DATA\redis.conf"
$redisConf | Out-File -FilePath $redisConfPath -Encoding ascii -Force

# Start Redis
$redisRunning = netstat -ano | Select-String ":6379.*LISTENING"
if (-not $redisRunning) {
    Write-Host "  Starting Redis..."
    $redisExe = Get-ChildItem $REDIS_DIR -Filter "redis-server.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($redisExe) {
        Start-Process $redisExe.FullName -ArgumentList $redisConfPath -WindowStyle Hidden
        Start-Sleep -Seconds 2
        if (netstat -ano | Select-String ":6379.*LISTENING") {
            Write-Host "  [OK] Redis started (data: $REDIS_DATA)" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Redis may not have started properly" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [WARN] redis-server.exe not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [SKIP] Redis already running on port 6379" -ForegroundColor Gray
}

# ============================================================
#  Step 4: Clone / Pull Project Code
# ============================================================
Write-Step "Step 4/8: Get Project Code"

$projectParent = Split-Path $PROJECT_DIR -Parent
if (-not (Test-Path $projectParent)) {
    New-Item -ItemType Directory -Path $projectParent -Force | Out-Null
}

if (Test-Path "$PROJECT_DIR\.git") {
    Write-Host "  Project exists, pulling latest..."
    Set-Location $PROJECT_DIR
    git pull origin main
} else {
    Write-Host "  Cloning repository..."
    git clone $GITHUB_REPO $PROJECT_DIR
    Set-Location $PROJECT_DIR
}
Write-Host "  [OK] Code ready: $PROJECT_DIR" -ForegroundColor Green

# ============================================================
#  Step 5: Create .env Config
# ============================================================
Write-Step "Step 5/8: Create Backend .env Config"

$envPath = Join-Path $PROJECT_DIR "backend\.env"

$envContent = @"
APP_ENV=development
APP_DEBUG=true
APP_SECRET_KEY=eds-secret-key-2026-change-in-production
APP_HOST=0.0.0.0
APP_PORT=8000

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=energy_tds
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$PASSWORD

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=energy_tds_meta
MONGO_USER=energy_mongo
MONGO_PASSWORD=$PASSWORD

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=energy_minio_access
MINIO_SECRET_KEY=$PASSWORD
MINIO_BUCKET=energy-tds
MINIO_USE_SSL=false

MQTT_BROKER=tcp://localhost:1883
MQTT_WS_URL=ws://localhost:8083/mqtt
MQTT_CLIENT_ID=energy-tds-backend
MQTT_USERNAME=energy_mqtt
MQTT_PASSWORD=$PASSWORD

RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=energy_rabbit
RABBITMQ_PASSWORD=$PASSWORD
RABBITMQ_VHOST=energy_tds

FISCO_CHANNEL_HOST=localhost
FISCO_CHANNEL_PORT=20200
FISCO_GROUP_ID=1
FISCO_SM_CRYPTO=true

FATE_COORDINATOR_HOST=localhost
FATE_COORDINATOR_PORT=9380
FATE_PARTY_ID=10000
FATE_FLOW_BASE_URL=http://localhost:9380
FATE_FLOW_API_PREFIX=/v2
FATE_FLOW_TIMEOUT=30.0
FATE_FLOW_MAX_RETRIES=3
FATE_FLOW_OPERATION_MODE=simulation

JWT_SECRET_KEY=eds-jwt-secret-2026-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
"@

[System.IO.File]::WriteAllText($envPath, $envContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "  [OK] Config written: $envPath" -ForegroundColor Green

# ============================================================
#  Step 6: Install Backend Python Deps + Init DB
# ============================================================
Write-Step "Step 6/8: Install Backend Deps + Init Database"

Set-Location "$PROJECT_DIR\backend"

Write-Host "  Installing Python packages..."
python -m pip install --upgrade pip 2>$null
python -m pip install -r requirements.txt --quiet

Write-Host "  Running database migrations..."
$env:PGPASSWORD = $PASSWORD
alembic upgrade head 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Database migration complete" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Alembic had issues, trying manual init..." -ForegroundColor Yellow
    python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"
    Write-Host "  [OK] Database tables created" -ForegroundColor Green
}

# ============================================================
#  Step 7: Build Frontend
# ============================================================
Write-Step "Step 7/8: Install Frontend Deps + Build"

Set-Location "$PROJECT_DIR\frontend"

Write-Host "  Installing npm packages (this may take a few minutes)..."
$env:NODE_OPTIONS = "--max-old-space-size=4096"
npm install --legacy-peer-deps 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] npm install had warnings, continuing..." -ForegroundColor Yellow
}

Write-Host "  Building frontend (this may take a few minutes)..."
npm run build 2>&1 | Out-Null

if (Test-Path "dist\index.html") {
    Write-Host "  [OK] Frontend build success" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Frontend build failed! Trying with increased memory..." -ForegroundColor Yellow
    $env:NODE_OPTIONS = "--max-old-space-size=8192"
    npm run build 2>&1 | Out-Null
    if (Test-Path "dist\index.html") {
        Write-Host "  [OK] Frontend build success (retry)" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Frontend build failed! Check errors above." -ForegroundColor Red
    }
}

# ============================================================
#  Step 8: Start Services + Firewall
# ============================================================
Write-Step "Step 8/8: Start Services + Firewall"

# Stop old processes
Write-Host "  Stopping old services..."
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "http.server|uvicorn"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Start backend (8000)
Write-Host "  Starting Backend API (port 8000)..."
Set-Location "$PROJECT_DIR\backend"
Start-Process python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" -WindowStyle Hidden
Write-Host "  [OK] Backend started" -ForegroundColor Green

# Start frontend (8080)
Write-Host "  Starting Frontend HTTP (port 8080)..."
$distDir = "$PROJECT_DIR\frontend\dist"
if (Test-Path $distDir) {
    Set-Location $distDir
    Start-Process python -ArgumentList "-m", "http.server", "8080" -WindowStyle Hidden
    Write-Host "  [OK] Frontend started" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] dist directory not found, frontend not started" -ForegroundColor Red
}

Start-Sleep -Seconds 5

# Firewall
Write-Host "  Opening firewall ports..."
netsh advfirewall firewall add rule name="EDS Frontend 8080" dir=in action=allow protocol=TCP localport=8080 | Out-Null
netsh advfirewall firewall add rule name="EDS Backend 8000" dir=in action=allow protocol=TCP localport=8000 | Out-Null
Write-Host "  [OK] Firewall rules added" -ForegroundColor Green

# ============================================================
#  Final Verification
# ============================================================
Write-Step "Final: Service Status Check"

$services = @(
    @{Name="PostgreSQL"; Port=5432; Required=$true},
    @{Name="Redis"; Port=6379; Required=$true},
    @{Name="Backend API"; Port=8000; Required=$true},
    @{Name="Frontend"; Port=8080; Required=$true}
)

$allOk = $true
foreach ($svc in $services) {
    $listening = netstat -ano | Select-String ":$($svc.Port).*LISTENING"
    if ($listening) {
        Write-Host "  [OK] $($svc.Name) (port $($svc.Port))" -ForegroundColor Green
    } else {
        if ($svc.Required) {
            Write-Host "  [FAIL] $($svc.Name) (port $($svc.Port)) - NOT RUNNING" -ForegroundColor Red
            $allOk = $false
        } else {
            Write-Host "  [SKIP] $($svc.Name) (port $($svc.Port)) - optional, not running" -ForegroundColor Gray
        }
    }
}

# ============================================================
#  Done
# ============================================================
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
if ($allOk) {
    Write-Host "  Deployment Complete - All Services Running!" -ForegroundColor Green
} else {
    Write-Host "  Deployment Finished with Issues" -ForegroundColor Yellow
    Write-Host "  Check the errors above and see TROUBLESHOOTING below" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  Frontend:  http://10.241.2.64:8080" -ForegroundColor White
Write-Host "  Backend:   http://10.241.2.64:8000" -ForegroundColor White
Write-Host "  API Docs:  http://10.241.2.64:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Software:  $SOFTWARE_DIR" -ForegroundColor Gray
Write-Host "  Data:      $DATA_DIR" -ForegroundColor Gray
Write-Host "  Project:   $PROJECT_DIR" -ForegroundColor Gray
Write-Host "  PG Data:   $PG_DATA" -ForegroundColor Gray
Write-Host "  Redis:     $REDIS_DIR" -ForegroundColor Gray
Write-Host "  Node:      $NODE_DIR" -ForegroundColor Gray
Write-Host ("=" * 60) -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })

if (-not $allOk) {
    Write-Host ""
    Write-Host "  TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "  - PostgreSQL failed: Download manually from https://www.postgresql.org/download/windows/" -ForegroundColor Gray
    Write-Host "  - Redis failed: Download from https://github.com/tporadowski/redis/releases" -ForegroundColor Gray
    Write-Host "  - Backend failed: Check $PROJECT_DIR\backend\logs\ for errors" -ForegroundColor Gray
    Write-Host "  - Frontend failed: Run 'cd $PROJECT_DIR\frontend && npm run build' manually" -ForegroundColor Gray
}

pause
