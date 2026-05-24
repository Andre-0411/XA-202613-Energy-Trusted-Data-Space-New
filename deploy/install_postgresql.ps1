# PostgreSQL 一键安装脚本
# 在服务器 10.241.2.64 上以管理员身份运行

param(
    [string]$PgPassword = "Andre0411",
    [string]$DbName = "energy_trusted",
    [string]$DbUser = "energy",
    [string]$DbPassword = "Andre0411"
)

Write-Host "=== PostgreSQL 安装脚本 ===" -ForegroundColor Cyan
Write-Host "数据库密码: $PgPassword" -ForegroundColor Yellow
Write-Host "业务数据库: $DbName" -ForegroundColor Yellow
Write-Host "业务用户: $DbUser" -ForegroundColor Yellow

# 1. 下载 PostgreSQL
$installerUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64.exe"
$installerPath = "C:\postgresql-installer.exe"

if (-not (Test-Path "C:\Program Files\PostgreSQL\16\bin\psql.exe")) {
    Write-Host "`n[1/4] 下载 PostgreSQL 安装程序..." -ForegroundColor Green
    if (-not (Test-Path $installerPath)) {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    }
    
    # 2. 静默安装
    Write-Host "[2/4] 安装 PostgreSQL..." -ForegroundColor Green
    Start-Process -FilePath $installerPath -ArgumentList @(
        "--mode", "unattended",
        "--superpassword", $PgPassword,
        "--serverport", "5432",
        "--datadir", "C:\PostgreSQL\data",
        "--install_runtimes", "0"
    ) -Wait -NoNewWindow
    
    Write-Host "PostgreSQL 安装完成!" -ForegroundColor Green
} else {
    Write-Host "PostgreSQL 已安装，跳过安装步骤" -ForegroundColor Yellow
}

# 3. 配置环境变量
$pgBin = "C:\Program Files\PostgreSQL\16\bin"
$env:Path = "$pgBin;$env:Path"

# 4. 创建数据库和用户
Write-Host "`n[3/4] 创建数据库和用户..." -ForegroundColor Green

$env:PGPASSWORD = $PgPassword

# 创建用户
& "$pgBin\psql.exe" -U postgres -c "CREATE USER $DbUser WITH PASSWORD '$DbPassword';" 2>$null
& "$pgBin\psql.exe" -U postgres -c "ALTER USER $DbUser CREATEDB;" 2>$null

# 创建数据库
& "$pgBin\psql.exe" -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser;" 2>$null
& "$pgBin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DbName TO $DbUser;" 2>$null

Write-Host "数据库创建完成!" -ForegroundColor Green

# 5. 创建 .env 文件
Write-Host "`n[4/4] 配置后端连接..." -ForegroundColor Green

$envContent = @"
DATABASE_URL=postgresql+asyncpg://${DbUser}:${DbPassword}@localhost:5432/${DbName}
SECRET_KEY=energy-trusted-secret-key-Andre0411
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${PgPassword}
"@

$backendDir = "D:\Andre\project\energy-trusted-data-space\backend"
$envFile = Join-Path $backendDir ".env"

# 备份原有 .env
if (Test-Path $envFile) {
    Copy-Item $envFile "$envFile.bak" -Force
}

Set-Content -Path $envFile -Value $envContent -Encoding UTF8
Write-Host ".env 文件已创建: $envFile" -ForegroundColor Green

# 6. 验证
Write-Host "`n=== 验证安装 ===" -ForegroundColor Cyan
& "$pgBin\psql.exe" -U postgres -c "\l" | Select-String $DbName
& "$pgBin\psql.exe" -U postgres -c "\du" | Select-String $DbUser

Write-Host "`n安装完成! 请重启 uvicorn 服务" -ForegroundColor Green
Write-Host "cd D:\Andre\project\energy-trusted-data-space\backend" -ForegroundColor Yellow
Write-Host "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
