"""
四大业务场景演示数据种子脚本
用于演示：电网调度、新能源消纳、虚拟电厂、电力市场
"""
import asyncio
import uuid
from datetime import datetime, timedelta
import random

from app.database import AsyncSessionLocal
from app.models.user import Organization, User


async def seed_demo_scenarios():
    """生成四大业务场景演示数据"""
    async with AsyncSessionLocal() as db:
        # 1. 创建演示组织
        orgs = [
            Organization(
                id=uuid.uuid4(), name="华能新能源山东公司", code="HNNE",
                level=2, status="active"
            ),
            Organization(
                id=uuid.uuid4(), name="三峡能源山东分公司", code="SXNE",
                level=2, status="active"
            ),
            Organization(
                id=uuid.uuid4(), name="国网山东电力公司", code="SGSD",
                level=1, status="active"
            ),
            Organization(
                id=uuid.uuid4(), name="大唐山东发电公司", code="DTSD",
                level=2, status="active"
            ),
            Organization(
                id=uuid.uuid4(), name="特锐德充电桩公司", code="TRD",
                level=2, status="active"
            ),
        ]
        for org in orgs:
            db.add(org)
        await db.commit()
        print(f"Created {len(orgs)} demo organizations")

        # 2. 创建演示用户（不同角色）
        users = [
            User(id=uuid.uuid4(), username="hn_admin", email="hn@example.com",
                 role="org_admin", organization_id=orgs[0].id, status="active"),
            User(id=uuid.uuid4(), username="sx_admin", email="sx@example.com",
                 role="org_admin", organization_id=orgs[1].id, status="active"),
            User(id=uuid.uuid4(), username="data_user", email="data@example.com",
                 role="data_access", organization_id=orgs[2].id, status="active"),
            User(id=uuid.uuid4(), username="product_dev", email="dev@example.com",
                 role="product_dev", organization_id=orgs[2].id, status="active"),
            User(id=uuid.uuid4(), username="demand_user", email="demand@example.com",
                 role="demand_publish", organization_id=orgs[3].id, status="active"),
        ]
        for user in users:
            db.add(user)
        await db.commit()
        print(f"Created {len(users)} demo users")

    print("Demo scenarios seed complete!")


if __name__ == "__main__":
    asyncio.run(seed_demo_scenarios())
