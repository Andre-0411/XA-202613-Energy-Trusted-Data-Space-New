"""Debug: upload and run a simple test"""
import paramiko
import time
import traceback

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)
    print("Connected!")

    # Write a simple test
    simple_test = '''
import urllib.request
import json
print("Starting test...", flush=True)
try:
    req = urllib.request.Request(
        "http://10.241.2.64:8000/api/v1/auth/login",
        data=b'{"username":"admin","password":"admin123"}',
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read().decode())
        tok = d.get("data", {}).get("access_token", "")
        print(f"Login OK, token length: {len(tok)}", flush=True)

        # Test a few endpoints
        headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
        endpoints = [
            "/api/v1/blockchain/evidence",
            "/api/v1/compute/fl/models",
            "/api/v1/data/sources",
            "/api/v1/connector-manage",
            "/api/v1/workflows",
            "/api/v1/product-market/search",
            "/api/v1/ops/alerts",
        ]
        for ep in endpoints:
            try:
                req2 = urllib.request.Request(f"http://10.241.2.64:8000{ep}", headers=headers, method="GET")
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    print(f"[PASS] {ep} -> {resp2.status}", flush=True)
            except urllib.error.HTTPError as e:
                print(f"[FAIL] {ep} -> {e.code}", flush=True)
            except Exception as e:
                print(f"[ERR] {ep} -> {e}", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
print("Done!", flush=True)
'''
    sftp = ssh.open_sftp()
    with sftp.open(r"D:\Andre\project\energy-trusted-data-space\simple_test.py", "w") as f:
        f.write(simple_test)
    sftp.close()
    print("Script uploaded!")

    cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -u simple_test.py'
    print(f"Running command...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)

    # Read output in chunks
    print("Reading output...")
    output = stdout.read().decode("utf-8", errors="replace")
    errs = stderr.read().decode("utf-8", errors="replace")
    print("--- STDOUT ---")
    print(output)
    if errs.strip():
        print("--- STDERR ---")
        print(errs[:500])

    ssh.close()
except Exception as e:
    print(f"Script error: {e}")
    traceback.print_exc()
