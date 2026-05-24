import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.241.2.64', username='zhouxuying', password='zhouxuying51')

# 查看 middleware/ 目录下有什么文件
stdin, stdout, stderr = ssh.exec_command(r'dir /b "D:\Andre\project\energy-trusted-data-space\backend\app\middleware"')
print('middleware/ contents:')
print(stdout.read().decode('gbk', errors='replace'))

# 确认 main.py 导入行
stdin, stdout, stderr = ssh.exec_command(r'type "D:\Andre\project\energy-trusted-data-space\backend\app\main.py"')
main_content = stdout.read().decode('gbk', errors='replace')
for i, line in enumerate(main_content.split('\n'), 1):
    if 'middleware' in line.lower() or 'csrf' in line.lower():
        print(f'Line {i}: {line.strip()}')

ssh.close()
