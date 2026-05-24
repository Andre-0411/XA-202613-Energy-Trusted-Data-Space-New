"""测试监控指标端点"""
import paramiko
import json

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)

    # 测试监控指标
    print("=== 测试 GET /api/v1/ops/monitoring/metrics ===")
    test_cmd = (
        'D:\\xujingyi\\anaconda3\\python.exe -c "'
        "import urllib.request, json; "
        "req = urllib.request.Request('http://127.0.0.1:8000/api/v1/ops/monitoring/metrics'); "
        "r = urllib.request.urlopen(req, timeout=15); "
        "data = json.loads(r.read()); "
        "print(json.dumps(data, indent=2, ensure_ascii=False))"
        '"'
    )
    stdin, stdout, stderr = client.exec_command(test_cmd, timeout=20)
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    print(f"响应: {out[:1000]}")
    if err:
        print(f"错误: {err[:500]}")

    client.close()

if __name__ == "__main__":
    main()
