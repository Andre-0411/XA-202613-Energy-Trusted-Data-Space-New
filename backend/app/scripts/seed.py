"""
种子数据脚本
填充初始数据（管理员用户、默认角色、默认策略等）
"""
import asyncio
import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def seed_data():
    """填充种子数据"""
    from app.database import init_db, close_db, AsyncSessionLocal
    from sqlalchemy import text

    print("🌱 初始化数据库连接...")
    await init_db()

    print("🌱 创建初始数据...")

    async with AsyncSessionLocal() as session:
        # 创建基础角色
        roles = [
            ("admin", "系统管理员", "拥有所有权限"),
            ("data_manager", "数据管理员", "数据读写权限"),
            ("compute_user", "计算用户", "计算任务权限"),
            ("auditor", "审计员", "只读审计权限"),
            ("operator", "运维人员", "运维管理权限"),
        ]

        for role_key, role_name, role_desc in roles:
            result = await session.execute(
                text(
                    "SELECT id FROM roles WHERE role_key = :key"
                ),
                {"key": role_key},
            )
            if not result.fetchone():
                await session.execute(
                    text(
                        "INSERT INTO roles (role_key, role_name, description) "
                        "VALUES (:key, :name, :desc)"
                    ),
                    {"key": role_key, "name": role_name, "desc": role_desc},
                )
                print(f"  ✓ 创建角色: {role_name}")

        await session.commit()

    print("🌱 种子数据填充完成！")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed_data())
