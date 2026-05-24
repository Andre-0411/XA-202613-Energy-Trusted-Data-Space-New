"""详细测试监控指标端点"""
import paramiko

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)

    test_cmd = (
        'D:\\xujingyi\\anaconda3\\python.exe -c "'
        "import urllib.request, json, traceback; "
        "try: "
        "  req = urllib.request.Request('http://127.0.0.1:8000/api/v1/ops/monitoring/metrics'); "
        "  r = urllib.request.urlopen(req, timeout=15); "
        "  data = r.read().decode(); "
        "  parsed = json.loads(data); "
        "  print('SUCCESS:', json.dumps(parsed, indent=2, ensure_ascii=False)[:800]); "
        "except urllib.error.HTTPError as e: "
        "  print('HTTP_ERROR:', e.code, e.reason); "
        "  print('BODY:', e.read().decode()[:800]); "
        "except Exception as e: "
        "  print('ERROR:', type(e).__name__, str(e)); "
        "  traceback.print_exc()"
        '"'
    )
    stdin, stdout, stderr = client.exec_command(test_cmd, timeout=20)
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    print(f"stdout: {out}")
    if err:
        print(f"stderr: {err[:500]}")

    # 也检查 uvicorn.log 的最新错误
    print("\n=== uvicorn.log 最新内容 ===")
    stdin, stdout, stderr = client.exec_command(
        'powershell -Command "Get-Content D:\\Andre\\project\\energy-trusted-data-space\\uvicorn.log -Tail 15"',
        timeout=10
    )
    print(stdout.read().decode("gbk", errors="replace"))

    client.close()

if __name__ == "__main__":
    main()
