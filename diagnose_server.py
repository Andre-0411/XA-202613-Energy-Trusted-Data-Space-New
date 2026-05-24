"""Diagnose server startup issues - check .env, port, and connectivity."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
BACKEND_DIR = r"D:\Andre\project\energy-trusted-data-space\backend"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"
PYTHON = r"D:\xujingyi\anaconda3\python.exe"

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=10)
    print(f"[OK] Connected to {HOST}")

    # Check .env file
    print("\n=== .env file ===")
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\.env 2>nul')
    if out:
        print(out[:1000])
    else:
        print("  No .env found in project root")
    
    out, _ = run_cmd(ssh, f'type {BACKEND_DIR}\\.env 2>nul')
    if out:
        print(f"\n  backend/.env:\n{out[:1000]}")
    else:
        print("  No .env found in backend")

    # Check PostgreSQL service
    print("\n=== PostgreSQL service ===")
    out, _ = run_cmd(ssh, 'sc query postgresql* 2>nul')
    if out:
        print(out[:500])
    else:
        out, _ = run_cmd(ssh, 'sc query postgres* 2>nul')
        print(out[:500] if out else "  No PostgreSQL service found")
    
    # Check if PostgreSQL is running
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":5432 " 2>nul')
    print(f"\n  Port 5432: {out[:300] if out else 'NOT FOUND'}")
    
    # Check what port 8000 looks like
    print("\n=== Port 8000 detailed ===")
    out, _ = run_cmd(ssh, 'netstat -ano | findstr "8000" 2>nul')
    print(out[:500] if out else "  No port 8000 entries")
    
    # Check python process details
    out, _ = run_cmd(ssh, 'tasklist /FI "PID eq 8656" /V /FO CSV 2>nul')
    print(f"\n  PID 8656: {out[:300]}")
    
    # Check if the server actually bound to the port
    print("\n=== Full uvicorn log ===")
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn.log 2>nul')
    print(out[:2000])
    
    # Check .env.example for expected config
    print("\n=== .env.example ===")
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\.env.example 2>nul')
    if out:
        print(out[:500])
    
    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
