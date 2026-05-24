"""Restart uvicorn on server with fixed .env"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.241.2.64', username='zhouxuying', password='zhouxuying51')

# Kill existing uvicorn by finding its PID
stdin, stdout, stderr = ssh.exec_command('wmic process where "CommandLine like \\"%uvicorn%\\"" get ProcessId 2>nul')
out = stdout.read().decode('gbk', errors='replace').strip()
print('Uvicorn PIDs:', out)

# Kill python processes on port 8000
stdin, stdout, stderr = ssh.exec_command('netstat -ano | findstr :8000 | findstr LISTENING')
out = stdout.read().decode('gbk', errors='replace').strip()
print('Port 8000:', out)
if out:
    for line in out.split('\n'):
        parts = line.strip().split()
        if len(parts) >= 5:
            pid = parts[4]
            print(f'Killing PID {pid}')
            ssh.exec_command(f'taskkill /F /PID {pid}')

time.sleep(2)

# Write a start script
sftp = ssh.open_sftp()
start_script = '@echo off\r\ncd /d D:\\Andre\\project\\energy-trusted-data-space\r\nD:\\xujingyi\\anaconda3\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend\r\n'
with sftp.open('D:/Andre/project/energy-trusted-data-space/start_backend.bat', 'w') as f:
    f.write(start_script)
sftp.close()

# Use schtasks to run it
stdin, stdout, stderr = ssh.exec_command('schtasks /Create /TN "UvicornRestart" /TR "D:\\Andre\\project\\energy-trusted-data-space\\start_backend.bat" /SC ONCE /ST 00:00 /F')
print('Create task:', stdout.read().decode('gbk', errors='replace').strip(), stderr.read().decode('gbk', errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command('schtasks /Run /TN "UvicornRestart"')
print('Run task:', stdout.read().decode('gbk', errors='replace').strip(), stderr.read().decode('gbk', errors='replace').strip())

time.sleep(15)

# Check port
stdin, stdout, stderr = ssh.exec_command('netstat -ano | findstr :8000 | findstr LISTENING')
out = stdout.read().decode('gbk', errors='replace').strip()
print('Port 8000 after restart:', out)

ssh.close()
