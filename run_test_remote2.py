"""Run full test on server via paramiko - write output to file"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS)

# Run test and redirect output to file
cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -u full_test.py > test_output.txt 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
exit_code = stdout.channel.recv_exit_status()
print(f"Exit code: {exit_code}")

# Wait a moment for file to be written
time.sleep(2)

# Read the output file via SFTP
sftp = ssh.open_sftp()
try:
    with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_output.txt", "r") as f:
        output = f.read().decode("utf-8", errors="replace")
        print(output)
except Exception as e:
    print(f"Error reading output: {e}")
sftp.close()

ssh.close()
