"""检查服务器上的 uvicorn 日志"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

# 检查 uvicorn 输出日志
cmds = [
    f'type "{PROJECT}\\backend_server.log" 2>nul',
    f'type "{PROJECT}\\backend.log" 2>nul',
    # 检查 schtask 运行状态
    'schtasks /Query /TN "ETDS-Backend" /FO LIST 2>nul',
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    if out:
        print(f"CMD: {cmd}")
        print(out[-2000:])  # 最后 2000 字符
        print()

# 直接测试 session 端点看错误
print("\n--- 直接测试 session 端点 ---")
test_cmd = (
    'powershell -Command "'
    '$login = Invoke-WebRequest -Uri http://localhost:8000/api/v1/auth/login -Method POST '
    '-Body \'{"username":"admin","password":"admin123","auth_type":"password"}\' '
    '-ContentType \'application/json\' -UseBasicParsing -TimeoutSec 10; '
    '$token = ($login.Content | ConvertFrom-Json).data.access_token; '
    'try { '
    '  $session = Invoke-WebRequest -Uri http://localhost:8000/api/v1/auth/session '
    '-Headers @{Authorization="Bearer $token"} -UseBasicParsing -TimeoutSec 10; '
    '  Write-Output "Session: $($session.StatusCode)"; '
    '  Write-Output $session.Content; '
    '} catch { '
    '  Write-Output "Error: $($_.Exception.Message)"; '
    '  Write-Output "Response: $($_.Exception.Response.StatusCode)"; '
    '  $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); '
    '  Write-Output $reader.ReadToEnd(); '
    '}"'
)
stdin, stdout, stderr = ssh.exec_command(test_cmd, timeout=30)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err:
    print(f"STDERR: {err}")

ssh.close()
