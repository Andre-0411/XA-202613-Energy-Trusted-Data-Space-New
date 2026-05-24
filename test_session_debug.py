"""调试 session 端点的 500 错误"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

def upload_text(ssh, path, content):
    sftp = ssh.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()

# 写一个直接调用 get_session 的测试脚本
debug_py = '''import asyncio
import sys
sys.path.insert(0, r"D:\\Andre\\project\\energy-trusted-data-space\\backend")

from app.database import get_db, AsyncSessionLocal
from app.services import auth_service
from sqlalchemy import select
from app.models.user import User

async def main():
    async with AsyncSessionLocal() as db:
        # 先查用户
        result = await db.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        if not user:
            print("ERROR: User 'admin' not found")
            return

        print(f"User found: {user.username} (id={user.id})")
        print(f"  role={user.role}")
        print(f"  did={user.did}")
        print(f"  org_id={user.organization_id}")
        print(f"  last_login_at={user.last_login_at}")

        # 测试 get_session
        try:
            session = await auth_service.get_session(db, str(user.id))
            print(f"\\nSession OK: {session}")
        except Exception as e:
            print(f"\\nSession ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(main())
'''

upload_text(ssh, f"{PROJECT}\\test_debug_session.py", debug_py)

stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_debug_session.py"', timeout=30)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print("STDOUT:")
print(out)
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
