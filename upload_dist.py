import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.84.80.39', username='root', password='Andre0411', timeout=10)

sftp = ssh.open_sftp()

local_dir = r'D:\Projects\energy-trusted-data-space\frontend\dist'
remote_dir = '/opt/energy-trusted-data-space/frontend/dist'

# Clean remote dist
stdin, stdout, stderr = ssh.exec_command(f'rm -rf {remote_dir} && mkdir -p {remote_dir}')
stdout.read()

# Upload function
uploaded = 0
for root, dirs, files in os.walk(local_dir):
    for d in dirs:
        local_path = os.path.join(root, d)
        rel = os.path.relpath(local_path, local_dir).replace(os.sep, '/')
        remote_path = f'{remote_dir}/{rel}'
        try:
            sftp.mkdir(remote_path)
        except:
            pass
    for f in files:
        local_path = os.path.join(root, f)
        rel = os.path.relpath(local_path, local_dir).replace(os.sep, '/')
        remote_path = f'{remote_dir}/{rel}'
        sftp.put(local_path, remote_path)
        uploaded += 1

print(f'Uploaded {uploaded} files to {remote_dir}')
sftp.close()
ssh.close()
