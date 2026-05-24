"""Deploy frontend dist to server 10.241.2.64"""
import paramiko
import os
import sys

SERVER = "10.241.2.64"
PORT = 22
USER = "zhouxuying"
PASS = "zhouxuying51"
REMOTE_FRONTEND_DIR = r"D:\Andre\project\energy-trusted-data-space\frontend\dist"
LOCAL_DIST_DIR = r"D:\Projects\energy-trusted-data-space\frontend\dist"

def upload_dir(sftp, sftp_client, local_dir, remote_dir):
    """Recursively upload directory"""
    uploaded = 0
    errors = []
    
    for root, dirs, files in os.walk(local_dir):
        # Calculate relative path
        rel_path = os.path.relpath(root, local_dir)
        remote_path = remote_dir if rel_path == '.' else f"{remote_dir}\\{rel_path.replace('/', '\\')}"
        
        # Create remote directory
        try:
            sftp_client.exec_command(f"if not exist \"{remote_path}\" mkdir \"{remote_path}\"")
        except:
            pass
        
        for filename in files:
            local_file = os.path.join(root, filename)
            remote_file = f"{remote_path}\\{filename}"
            
            try:
                sftp.put(local_file, remote_file)
                uploaded += 1
                if uploaded % 20 == 0:
                    print(f"  Uploaded {uploaded} files...")
            except Exception as e:
                errors.append((local_file, str(e)))
                print(f"  ERROR uploading {filename}: {e}")
    
    return uploaded, errors

def main():
    print(f"Connecting to {SERVER}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, PORT, USER, PASS, timeout=30)
    sftp = ssh.open_sftp()
    
    print("Connected. Uploading dist files...")
    
    # Clear old dist
    stdin, stdout, stderr = ssh.exec_command(
        f'if exist "{REMOTE_FRONTEND_DIR}" rmdir /s /q "{REMOTE_FRONTEND_DIR}"'
    )
    stdout.read()
    
    # Create fresh dist dir
    stdin, stdout, stderr = ssh.exec_command(f'mkdir "{REMOTE_FRONTEND_DIR}"')
    stdout.read()
    
    uploaded, errors = upload_dir(sftp, ssh, LOCAL_DIST_DIR, REMOTE_FRONTEND_DIR)
    
    print(f"\nUpload complete: {uploaded} files uploaded, {len(errors)} errors")
    
    # Verify
    stdin, stdout, stderr = ssh.exec_command(
        f'dir /s /b "{REMOTE_FRONTEND_DIR}" 2>nul | find /c /v ""'
    )
    count = stdout.read().decode('gbk', errors='replace').strip()
    print(f"Remote file count: {count}")
    
    sftp.close()
    ssh.close()
    print("Done!")

if __name__ == "__main__":
    main()
