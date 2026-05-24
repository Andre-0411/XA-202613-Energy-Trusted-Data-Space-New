"""Run test and get full results"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS, timeout=30)

# Run test
cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -u full_test.py > test_output.txt 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
exit_code = stdout.channel.recv_exit_status()
time.sleep(3)

# Read output via SFTP with proper encoding
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_output.txt", "r") as f:
    raw = f.read()
    # Try different encodings
    for enc in ["utf-8", "gbk", "cp936", "latin1"]:
        try:
            output = raw.decode(enc)
            break
        except:
            continue
    else:
        output = raw.decode("utf-8", errors="replace")

print(output)

# Also save locally
with open("D:/Projects/energy-trusted-data-space/test_results_final.txt", "w", encoding="utf-8") as f:
    f.write(output)

sftp.close()
ssh.close()
print("\nResults saved to test_results_final.txt")
