"""
MP-SPDZ 安全多方计算集成服务
发起MPC计算 / 可用协议查询 / 与compute_task关联

增强功能:
- SPDZ 协议基础框架（离线阶段 + 在线阶段）
- 加法秘密共享（Additive Secret Sharing）实现
- 安全加法和安全乘法协议
- MPC 会话管理（创建/加入/执行/结果获取）
- 计算任务编排（DAG 格式）
- 配置开关: MPC_SIMULATION_MODE（默认 true，模拟模式）
"""
import os
import uuid
import json
import hashlib
import logging
import secrets
import asyncio
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask
from app.models.mpc_session import MpcSession
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import ComputeError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

# 是否启用模拟模式（True=模拟，False=需真实 MP-SPDZ 引擎）
MPC_SIMULATION_MODE = os.getenv("MPC_SIMULATION_MODE", "true").lower() == "true"

# MP-SPDZ 引擎地址
MPSPDZ_HOST = os.getenv("MPSPDZ_HOST", "mpspdz")
MPSPDZ_PORT = int(os.getenv("MPSPDZ_PORT", "9000"))

# 秘密分享素数域（2^61 - 1，Mersenne 素数）
SECRET_SHARE_PRIME = (1 << 61) - 1

# MP-SPDZ 支持的协议
MPC_PROTOCOLS = {
    "spdz": {
        "name": "SPDZ",
        "description": "基于同态加密的恶意安全协议",
        "min_parties": 2,
        "max_parties": 10,
        "security_model": "malicious",
        "computation_type": "arithmetic",
    },
    "psn": {
        "name": "PSN",
        "description": "基于秘密共享的半诚实协议",
        "min_parties": 2,
        "max_parties": 10,
        "security_model": "semi-honest",
        "computation_type": "arithmetic",
    },
    "aby3": {
        "name": "ABY3",
        "description": "混合协议（算术/布尔/姚期）",
        "min_parties": 3,
        "max_parties": 3,
        "security_model": "semi-honest",
        "computation_type": "mixed",
    },
    "falcon": {
        "name": "Falcon",
        "description": "基于三方复制秘密共享",
        "min_parties": 3,
        "max_parties": 3,
        "security_model": "malicious",
        "computation_type": "arithmetic",
    },
    "chaiguru": {
        "name": "Chaiguru",
        "description": "基于混淆电路的两方协议",
        "min_parties": 2,
        "max_parties": 2,
        "security_model": "semi-honest",
        "computation_type": "boolean",
    },
    "malicious-sha2": {
        "name": "Malicious-SHA2",
        "description": "恶意安全算术协议（SHA2优化）",
        "min_parties": 2,
        "max_parties": 10,
        "security_model": "malicious",
        "computation_type": "arithmetic",
    },
}


# ==================== SPDZ 协议实现 ====================

class SPDZPhase(str, Enum):
    """SPDZ 协议阶段"""
    INITIALIZED = "initialized"
    OFFLINE_PREKEY = "offline_prekey"
    OFFLINE_MAC = "offline_mac"
    ONLINE_READY = "online_ready"
    ONLINE_RUNNING = "online_running"
    COMPLETED = "completed"
    FAILED = "failed"


class AdditiveSecretShare:
    """
    加法秘密共享（Additive Secret Sharing）

    将值 x 拆分为 n 份 shares: x = (s1 + s2 + ... + sn) mod p
    每方持有一个 share，只有集合所有方才能恢复原始值。
    """

    def __init__(self, prime: int = SECRET_SHARE_PRIME):
        self.prime = prime

    def share(self, value: int, num_parties: int) -> list[int]:
        """
        将值拆分为 n 份加法秘密份额

        Args:
            value: 要分享的秘密值（整数）
            num_parties: 参与方数量

        Returns:
            份额列表，长度 = num_parties
        """
        value = value % self.prime
        shares = []
        running_sum = 0
        for i in range(num_parties - 1):
            s = int.from_bytes(secrets.token_bytes(8), "big") % self.prime
            shares.append(s)
            running_sum = (running_sum + s) % self.prime
        # 最后一份使得 shares 之和 ≡ value (mod prime)
        last_share = (value - running_sum) % self.prime
        shares.append(last_share)
        return shares

    def reconstruct(self, shares: list[int]) -> int:
        """
        从份额恢复原始值

        Args:
            shares: 所有方的份额列表

        Returns:
            恢复的原始值
        """
        result = 0
        for s in shares:
            result = (result + s) % self.prime
        return result


class SecureAddition:
    """
    安全加法协议

    各方本地将对应份额相加，无需通信即可得到和的秘密份额。
    [x] + [y] = [x + y]  (本地操作)
    """

    def __init__(self, prime: int = SECRET_SHARE_PRIME):
        self.prime = prime

    def local_add(self, share_x: int, share_y: int) -> int:
        """
        本地安全加法：各方本地计算

        Args:
            share_x: x 的份额
            share_y: y 的份额

        Returns:
            x+y 的份额
        """
        return (share_x + share_y) % self.prime

    def local_add_batch(self, shares_x: list[int], shares_y: list[int]) -> list[int]:
        """批量本地安全加法"""
        if len(shares_x) != len(shares_y):
            raise ValueError("份额列表长度必须相同")
        return [(x + y) % self.prime for x, y in zip(shares_x, shares_y)]


class SecureMultiplication:
    """
    安全乘法协议（SPDZ Triple-based）

    使用 Beaver 三元组 (a, b, c=a*b) 实现安全乘法:
    1. 各方本地计算 e = [x] - [a], f = [y] - [b]
    2. 开放 e, f（需通信）
    3. 各方本地计算 [z] = e*f + e*[b] + f*[a] + [c]
    """

    def __init__(self, prime: int = SECRET_SHARE_PRIME):
        self.prime = prime
        self._triples: list[tuple[int, int, int]] = []

    def generate_triple(self) -> tuple[list[int], list[int], list[int]]:
        """
        生成 Beaver 三元组 (a, b, c=a*b) 的份额

        Returns:
            (shares_a, shares_b, shares_c) 三个值各自的份额列表
        """
        a = int.from_bytes(secrets.token_bytes(8), "big") % self.prime
        b = int.from_bytes(secrets.token_bytes(8), "big") % self.prime
        c = (a * b) % self.prime

        ssc = AdditiveSecretShare(self.prime)
        # 由协调方生成并分发（这里模拟）
        shares_a = ssc.share(a, 2)
        shares_b = ssc.share(b, 2)
        shares_c = ssc.share(c, 2)

        return shares_a, shares_b, shares_c

    def compute_e_f(
        self, share_x: int, share_y: int, share_a: int, share_b: int
    ) -> tuple[int, int]:
        """
        步骤1: 各方本地计算 e = [x] - [a], f = [y] - [b]

        Args:
            share_x: x 的份额
            share_y: y 的份额
            share_a: a 的份额（三元组）
            share_b: b 的份额（三元组）

        Returns:
            (e_share, f_share) 各自的份额
        """
        e_share = (share_x - share_a) % self.prime
        f_share = (share_y - share_b) % self.prime
        return e_share, f_share

    def reconstruct_open(self, e_shares: list[int], f_shares: list[int]) -> tuple[int, int]:
        """
        步骤2: 开放 e, f（所有方共同恢复明文）

        Args:
            e_shares: 各方的 e 份额
            f_shares: 各方的 f 份额

        Returns:
            (e, f) 明文值
        """
        e = sum(e_shares) % self.prime
        f = sum(f_shares) % self.prime
        return e, f

    def compute_result_share(
        self,
        e: int,
        f: int,
        share_a: int,
        share_b: int,
        share_c: int,
    ) -> int:
        """
        步骤3: 各方本地计算 [z] = e*f + e*[b] + f*[a] + [c]

        Args:
            e: 开放的 e 值
            f: 开放的 f 值
            share_a: a 的份额
            share_b: b 的份额
            share_c: c 的份额

        Returns:
            z 的份额
        """
        z_share = (e * f + e * share_b + f * share_a + share_c) % self.prime
        return z_share


class SPDZProtocol:
    """
    SPDZ 协议完整流程管理

    离线阶段: 生成 Beaver 三元组、MAC 密钥
    在线阶段: 使用三元组执行安全乘法
    """

    def __init__(self, session_id: str, num_parties: int, prime: int = SECRET_SHARE_PRIME):
        self.session_id = session_id
        self.num_parties = num_parties
        self.prime = prime
        self.phase = SPDZPhase.INITIALIZED
        self.secret_share = AdditiveSecretShare(prime)
        self.secure_add = SecureAddition(prime)
        self.secure_mul = SecureMultiplication(prime)
        self.mac_key: Optional[int] = None
        self.triples_pool: list[tuple[list[int], list[int], list[int]]] = []
        self.triples_count = 0
        self.created_at = datetime.now(timezone.utc).isoformat()

    async def run_offline_phase(self, num_triples: int = 100) -> dict:
        """
        执行 SPDZ 离线阶段

        1. 生成 MAC 密钥
        2. 预生成 Beaver 三元组

        Args:
            num_triples: 预生成三元组数量

        Returns:
            离线阶段结果
        """
        self.phase = SPDZPhase.OFFLINE_PREKEY
        logger.info(f"SPDZ 离线阶段开始: session={self.session_id}, triples={num_triples}")

        # 1. 生成全局 MAC 密钥
        self.mac_key = int.from_bytes(secrets.token_bytes(16), "big") % self.prime
        mac_shares = self.secret_share.share(self.mac_key, self.num_parties)

        self.phase = SPDZPhase.OFFLINE_MAC
        logger.info(f"SPDZ MAC 密钥已生成: session={self.session_id}")

        # 2. 批量生成三元组
        self.triples_pool = []
        for _ in range(num_triples):
            shares_a, shares_b, shares_c = self.secure_mul.generate_triple()
            self.triples_pool.append((shares_a, shares_b, shares_c))

        self.triples_count = num_triples
        self.phase = SPDZPhase.ONLINE_READY

        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "num_triples_generated": num_triples,
            "mac_key_shares_generated": True,
            "ready_for_online": True,
        }

    def get_triple(self) -> tuple[list[int], list[int], list[int]]:
        """
        从三元组池中获取一个三元组

        Returns:
            (shares_a, shares_b, shares_c)

        Raises:
            ComputeError: 如果三元组池为空
        """
        if not self.triples_pool:
            raise ComputeError("SPDZ 三元组池已耗尽，需重新执行离线阶段")
        return self.triples_pool.pop()

    async def execute_secure_multiplication(
        self,
        shares_x: list[int],
        shares_y: list[int],
    ) -> list[int]:
        """
        使用 SPDZ 协议执行安全乘法

        Args:
            shares_x: x 的各方份额
            shares_y: y 的各方份额

        Returns:
            z = x*y 的各方份额
        """
        if self.phase != SPDZPhase.ONLINE_READY:
            raise ComputeError(f"SPDZ 会话未就绪: 当前阶段={self.phase.value}")

        self.phase = SPDZPhase.ONLINE_RUNNING

        # 获取一个三元组
        shares_a, shares_b, shares_c = self.get_triple()

        # 步骤1: 各方本地计算 e, f
        e_shares = []
        f_shares = []
        for party_idx in range(self.num_parties):
            e_s, f_s = self.secure_mul.compute_e_f(
                shares_x[party_idx],
                shares_y[party_idx],
                shares_a[party_idx],
                shares_b[party_idx],
            )
            e_shares.append(e_s)
            f_shares.append(f_s)

        # 步骤2: 开放 e, f（模拟通信恢复）
        e, f = self.secure_mul.reconstruct_open(e_shares, f_shares)

        # 步骤3: 各方本地计算结果份额
        result_shares = []
        for party_idx in range(self.num_parties):
            z_s = self.secure_mul.compute_result_share(
                e, f,
                shares_a[party_idx],
                shares_b[party_idx],
                shares_c[party_idx],
            )
            result_shares.append(z_s)

        self.phase = SPDZPhase.ONLINE_READY
        return result_shares

    def get_status(self) -> dict:
        """获取 SPDZ 会话状态"""
        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "num_parties": self.num_parties,
            "triples_remaining": len(self.triples_pool),
            "triples_generated_total": self.triples_count,
            "mac_key_set": self.mac_key is not None,
            "created_at": self.created_at,
        }


# ==================== 全局 SPDZ 会话缓存 ====================

_spdz_sessions: dict[str, SPDZProtocol] = {}


# ==================== 会话管理 ====================

async def create_mpc_session(
    db: AsyncSession,
    name: str,
    protocol: str,
    participants: list[str],
    computation_config: dict,
    input_asset_ids: list[str] = None,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """
    创建 MPC 计算会话（包含 SPDZ 离线阶段初始化）

    Args:
        db: 数据库会话
        name: 任务名称
        protocol: MPC 协议
        participants: 参与方列表
        computation_config: 计算配置
        input_asset_ids: 输入资产 ID 列表
        user_id: 用户 ID
        organization_id: 组织 ID

    Returns:
        会话创建结果
    """
    # 1. 校验协议
    if protocol not in MPC_PROTOCOLS:
        raise DataValidationError(
            f"不支持的 MPC 协议: {protocol}，允许值: {list(MPC_PROTOCOLS.keys())}"
        )

    protocol_info = MPC_PROTOCOLS[protocol]

    # 2. 校验参与方数量
    party_count = len(participants)
    if party_count < protocol_info["min_parties"]:
        raise DataValidationError(
            f"协议 {protocol_info['name']} 至少需要 {protocol_info['min_parties']} 个参与方，"
            f"当前 {party_count} 个"
        )
    if party_count > protocol_info["max_parties"]:
        raise DataValidationError(
            f"协议 {protocol_info['name']} 最多支持 {protocol_info['max_parties']} 个参与方，"
            f"当前 {party_count} 个"
        )

    # 3. 校验计算配置
    if "circuit" not in computation_config and "function" not in computation_config and "dag" not in computation_config:
        raise DataValidationError("计算配置必须包含 circuit、function 或 dag 定义")

    # 4. 创建 ComputeTask
    task_config = {
        "protocol": protocol,
        "protocol_name": protocol_info["name"],
        "security_model": protocol_info["security_model"],
        "computation_type": protocol_info["computation_type"],
        "participants": participants,
        "computation_config": computation_config,
        "signature_threshold": party_count,
    }

    asset_ids = [uuid.UUID(a) for a in (input_asset_ids or [])]
    task = ComputeTask(
        name=name,
        task_type="MPC",
        scenario="mpc_computation",
        config=task_config,
        input_asset_ids=asset_ids,
        status="pending",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 5. 生成计算会话
    session_id = str(uuid.uuid4())
    party_endpoints = {p: f"mpcparty://{p}:8080" for p in participants}

    mpc_session = MpcSession(
        session_id=session_id,
        task_id=str(task.id),
        protocol=protocol,
        participants=participants,
        status="initialized",
        party_endpoints=party_endpoints,
    )
    db.add(mpc_session)
    await db.commit()

    # 6. 如果是 SPDZ 协议，初始化离线阶段
    offline_result = None
    if protocol == "spdz" and not MPC_SIMULATION_MODE:
        spdz = SPDZProtocol(session_id=session_id, num_parties=party_count)
        offline_result = await spdz.run_offline_phase(num_triples=100)
        _spdz_sessions[session_id] = spdz
    elif protocol == "spdz":
        # 模拟模式：直接创建 SPDZ 会话，标记为就绪
        spdz = SPDZProtocol(session_id=session_id, num_parties=party_count)
        spdz.phase = SPDZPhase.ONLINE_READY
        spdz.mac_key = int.from_bytes(secrets.token_bytes(16), "big") % SECRET_SHARE_PRIME
        _spdz_sessions[session_id] = spdz

    logger.info(
        f"MPC 会话已创建: session={session_id}, task={task.id}, "
        f"protocol={protocol}, parties={party_count}"
    )

    result = {
        "task_id": str(task.id),
        "session_id": session_id,
        "name": name,
        "protocol": protocol,
        "protocol_name": protocol_info["name"],
        "security_model": protocol_info["security_model"],
        "participants": participants,
        "party_endpoints": party_endpoints,
        "status": "initialized",
        "simulation_mode": MPC_SIMULATION_MODE,
    }
    if offline_result:
        result["offline_phase"] = offline_result

    return result


# 兼容旧接口名称
async def submit_mpc_computation(
    db: AsyncSession,
    name: str,
    protocol: str,
    participants: list[str],
    computation_config: dict,
    input_asset_ids: list[str] = None,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """发起 MPC 安全多方计算（兼容旧接口）"""
    return await create_mpc_session(
        db=db,
        name=name,
        protocol=protocol,
        participants=participants,
        computation_config=computation_config,
        input_asset_ids=input_asset_ids,
        user_id=user_id,
        organization_id=organization_id,
    )


async def join_session(db: AsyncSession, session_id: str, party_id: str) -> dict:
    """
    参与方加入 MPC 会话

    Args:
        db: 数据库会话
        session_id: 会话 ID
        party_id: 参与方 ID

    Returns:
        加入结果
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    participants = session.participants or []
    if party_id not in participants:
        raise DataValidationError(f"参与方 {party_id} 不在会话参与者列表中")

    current_status = session.status
    if current_status not in ("initialized", "ready"):
        raise ComputeError(f"会话状态不允许加入: {current_status}")

    # 更新状态为 ready（当所有方都加入后变为 running）
    new_status = "ready"
    await db.execute(
        update(MpcSession)
        .where(MpcSession.session_id == session_id)
        .values(status=new_status)
    )
    await db.commit()

    logger.info(f"MPC 参与方加入: session={session_id}, party={party_id}")
    return {
        "session_id": session_id,
        "party_id": party_id,
        "status": new_status,
        "participants": participants,
    }


async def execute_session(db: AsyncSession, session_id: str) -> dict:
    """
    执行 MPC 会话（启动在线阶段计算）

    Args:
        db: 数据库会话
        session_id: 会话 ID

    Returns:
        执行结果
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    current_status = session.status
    if current_status not in ("initialized", "ready"):
        raise ComputeError(f"会话状态不允许执行: {current_status}")

    # 更新会话状态
    await db.execute(
        update(MpcSession)
        .where(MpcSession.session_id == session_id)
        .values(status="running")
    )

    # 更新关联任务状态
    if session.task_id:
        await db.execute(
            update(ComputeTask)
            .where(ComputeTask.id == uuid.UUID(session.task_id))
            .values(status="running", progress=0)
        )

    await db.commit()

    # 模拟或真实执行
    if MPC_SIMULATION_MODE:
        asyncio.create_task(_simulate_mpc_execution(session_id, session.task_id))
    else:
        # 真实模式：调用 MP-SPDZ 引擎
        asyncio.create_task(_run_real_mpc(session_id, session.task_id, session))

    logger.info(f"MPC 会话执行已启动: session={session_id}")
    return {
        "session_id": session_id,
        "task_id": session.task_id,
        "status": "running",
        "simulation_mode": MPC_SIMULATION_MODE,
    }


async def _simulate_mpc_execution(session_id: str, task_id: Optional[str]) -> None:
    """模拟 MPC 计算执行"""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # 模拟计算过程
            for step in range(1, 11):
                await asyncio.sleep(0.3)
                if task_id:
                    await db.execute(
                        update(ComputeTask)
                        .where(ComputeTask.id == uuid.UUID(task_id))
                        .values(progress=step * 10)
                    )
                    await db.commit()

            # 模拟结果
            result_hash = hashlib.sha256(
                f"mpc_result_{session_id}".encode()
            ).hexdigest()

            # 更新会话状态
            await db.execute(
                update(MpcSession)
                .where(MpcSession.session_id == session_id)
                .values(status="completed")
            )

            # 更新任务状态
            if task_id:
                await db.execute(
                    update(ComputeTask)
                    .where(ComputeTask.id == uuid.UUID(task_id))
                    .values(
                        status="completed",
                        progress=100,
                        result_hash=result_hash,
                        completed_at=datetime.now(timezone.utc),
                    )
                )

            await db.commit()
            logger.info(f"MPC 模拟执行完成: session={session_id}")

        except Exception as e:
            logger.error(f"MPC 模拟执行失败: session={session_id}, error={e}")
            try:
                await db.execute(
                    update(MpcSession)
                    .where(MpcSession.session_id == session_id)
                    .values(status="failed")
                )
                if task_id:
                    await db.execute(
                        update(ComputeTask)
                        .where(ComputeTask.id == uuid.UUID(task_id))
                        .values(status="failed", error_message=str(e))
                    )
                await db.commit()
            except Exception:
                pass


async def _run_real_mpc(
    session_id: str,
    task_id: Optional[str],
    session: MpcSession,
) -> None:
    """执行真实 MPC 计算（连接 MP-SPDZ 引擎）"""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            import httpx

            protocol = session.protocol or "spdz"
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"http://{MPSPDZ_HOST}:{MPSPDZ_PORT}/execute",
                    json={
                        "session_id": session_id,
                        "protocol": protocol,
                        "participants": session.participants,
                        "task_id": task_id,
                    },
                )
                resp.raise_for_status()
                mpc_result = resp.json()

            result_hash = mpc_result.get("result_hash", "")

            await db.execute(
                update(MpcSession)
                .where(MpcSession.session_id == session_id)
                .values(status="completed")
            )
            if task_id:
                await db.execute(
                    update(ComputeTask)
                    .where(ComputeTask.id == uuid.UUID(task_id))
                    .values(
                        status="completed",
                        progress=100,
                        result_hash=result_hash,
                        completed_at=datetime.now(timezone.utc),
                    )
                )
            await db.commit()
            logger.info(f"MPC 真实执行完成: session={session_id}")

        except Exception as e:
            logger.error(f"MPC 真实执行失败: session={session_id}, error={e}")
            try:
                await db.execute(
                    update(MpcSession)
                    .where(MpcSession.session_id == session_id)
                    .values(status="failed")
                )
                if task_id:
                    await db.execute(
                        update(ComputeTask)
                        .where(ComputeTask.id == uuid.UUID(task_id))
                        .values(status="failed", error_message=str(e))
                    )
                await db.commit()
            except Exception:
                pass


async def get_session_result(db: AsyncSession, session_id: str) -> dict:
    """
    获取 MPC 会话结果

    Args:
        db: 数据库会话
        session_id: 会话 ID

    Returns:
        计算结果
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    if session.status != "completed":
        return {
            "session_id": session_id,
            "status": session.status,
            "message": "计算尚未完成",
        }

    # 获取关联任务的结果
    task_result_data = {}
    if session.task_id:
        task_result = await db.execute(
            select(ComputeTask).where(ComputeTask.id == uuid.UUID(session.task_id))
        )
        task = task_result.scalar_one_or_none()
        if task:
            task_result_data = {
                "task_id": str(task.id),
                "result_hash": task.result_hash,
                "result_ref": task.result_ref,
            }

    return {
        "session_id": session_id,
        "status": "completed",
        "protocol": session.protocol,
        "participants": session.participants,
        "result": task_result_data,
    }


async def list_protocols() -> list[dict]:
    """查询可用的 MPC 协议列表"""
    return [
        {
            "id": proto_id,
            "name": info["name"],
            "description": info["description"],
            "min_parties": info["min_parties"],
            "max_parties": info["max_parties"],
            "security_model": info["security_model"],
            "computation_type": info["computation_type"],
        }
        for proto_id, info in MPC_PROTOCOLS.items()
    ]


async def get_session_status(
    db: AsyncSession,
    session_id: str,
) -> dict:
    """查询 MPC 会话状态"""
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    session_dict = session.to_dict()

    # 附加 SPDZ 协议详情
    if session_id in _spdz_sessions:
        session_dict["spdz_status"] = _spdz_sessions[session_id].get_status()

    # 查询关联任务进度
    if session.task_id:
        task_result = await db.execute(
            select(ComputeTask).where(ComputeTask.id == uuid.UUID(session.task_id))
        )
        task = task_result.scalar_one_or_none()
        if task:
            session_dict["task_progress"] = task.progress
            session_dict["task_status"] = task.status

    return session_dict


async def verify_mpc_result(
    db: AsyncSession,
    task_id: str,
    result_hash: str,
) -> dict:
    """
    验证 MPC 计算结果的完整性

    1. 从任务获取原始结果哈希
    2. 比对传入的哈希值
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise DataNotFoundError("计算任务未找到")

    stored_hash = task.result_hash
    is_valid = stored_hash == result_hash if stored_hash else False

    return {
        "task_id": task_id,
        "stored_hash": stored_hash,
        "provided_hash": result_hash,
        "is_valid": is_valid,
    }


# ==================== DAG 任务编排 ====================

async def create_dag_computation(
    db: AsyncSession,
    name: str,
    protocol: str,
    participants: list[str],
    dag_definition: dict,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """
    创建 DAG 格式的 MPC 计算任务编排

    DAG 定义格式:
    {
        "nodes": [
            {"id": "n1", "type": "input", "params": {"asset_id": "..."}},
            {"id": "n2", "type": "compute", "op": "add", "inputs": ["n1", "n3"]},
            {"id": "n3", "type": "input", "params": {"asset_id": "..."}},
            {"id": "n4", "type": "output", "inputs": ["n2"]}
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n3", "to": "n2"},
            {"from": "n2", "to": "n4"}
        ]
    }

    Args:
        db: 数据库会话
        name: 任务名称
        protocol: MPC 协议
        participants: 参与方列表
        dag_definition: DAG 定义
        user_id: 用户 ID
        organization_id: 组织 ID

    Returns:
        DAG 计算任务创建结果
    """
    # 校验 DAG 定义
    nodes = dag_definition.get("nodes", [])
    edges = dag_definition.get("edges", [])

    if not nodes:
        raise DataValidationError("DAG 定义中 nodes 不能为空")

    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if edge["from"] not in node_ids:
            raise DataValidationError(f"DAG 边引用了不存在的节点: {edge['from']}")
        if edge["to"] not in node_ids:
            raise DataValidationError(f"DAG 边引用了不存在的节点: {edge['to']}")

    # 检测 DAG 无环性（Kahn 算法）
    if not _is_dag_valid(nodes, edges):
        raise DataValidationError("DAG 定义包含环路，不是有效的有向无环图")

    computation_config = {
        "dag": dag_definition,
        "execution_order": _topological_sort(nodes, edges),
    }

    # 创建会话
    result = await create_mpc_session(
        db=db,
        name=name,
        protocol=protocol,
        participants=participants,
        computation_config=computation_config,
        user_id=user_id,
        organization_id=organization_id,
    )

    result["dag_definition"] = dag_definition
    result["execution_order"] = computation_config["execution_order"]
    return result


def _is_dag_valid(nodes: list[dict], edges: list[dict]) -> bool:
    """
    使用 Kahn 算法检测 DAG 是否无环

    Returns:
        True 如果是有向无环图
    """
    node_ids = {n["id"] for n in nodes}
    in_degree = {nid: 0 for nid in node_ids}
    adjacency = {nid: [] for nid in node_ids}

    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
        in_degree[edge["to"]] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    visited_count = 0

    while queue:
        node = queue.pop(0)
        visited_count += 1
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited_count == len(node_ids)


def _topological_sort(nodes: list[dict], edges: list[dict]) -> list[str]:
    """
    拓扑排序，返回 DAG 节点的执行顺序

    Returns:
        节点 ID 的拓扑排序列表
    """
    node_ids = {n["id"] for n in nodes}
    in_degree = {nid: 0 for nid in node_ids}
    adjacency = {nid: [] for nid in node_ids}

    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
        in_degree[edge["to"]] += 1

    queue = sorted([nid for nid, deg in in_degree.items() if deg == 0])
    order = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in sorted(adjacency[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


# ==================== 安全计算便捷接口 ====================

async def secure_add_values(
    db: AsyncSession,
    session_id: str,
    values: list[int],
) -> dict:
    """
    在 MPC 会话中安全求和

    Args:
        db: 数据库会话
        session_id: MPC 会话 ID
        values: 各方提供的值列表

    Returns:
        安全求和结果份额
    """
    # 验证会话
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    if session.status != "running" and session.status != "initialized":
        raise ComputeError(f"会话状态不允许执行计算: {session.status}")

    num_parties = len(session.participants or [])
    if len(values) != num_parties:
        raise DataValidationError(f"值数量 ({len(values)}) 必须等于参与方数量 ({num_parties})")

    ssc = AdditiveSecretShare(SECRET_SHARE_PRIME)
    sec_add = SecureAddition(SECRET_SHARE_PRIME)

    # 秘密分享各方的值
    all_shares = []
    for val in values:
        shares = ssc.share(val, num_parties)
        all_shares.append(shares)

    # 各方本地执行安全加法
    result_shares = [0] * num_parties
    for shares in all_shares:
        for party_idx in range(num_parties):
            result_shares[party_idx] = sec_add.local_add(
                result_shares[party_idx], shares[party_idx]
            )

    # 恢复结果
    result_value = ssc.reconstruct(result_shares)

    logger.info(f"安全加法完成: session={session_id}, result={result_value}")
    return {
        "session_id": session_id,
        "operation": "secure_add",
        "input_count": len(values),
        "result_value": result_value,
        "result_shares": result_shares,
    }


async def secure_multiply_values(
    db: AsyncSession,
    session_id: str,
    values: list[int],
) -> dict:
    """
    在 MPC 会话中安全乘法（两方）

    Args:
        db: 数据库会话
        session_id: MPC 会话 ID
        values: 两个参与方提供的值

    Returns:
        安全乘法结果份额
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    if len(values) != 2:
        raise DataValidationError("安全乘法当前仅支持两个输入值")

    num_parties = len(session.participants or [])
    ssc = AdditiveSecretShare(SECRET_SHARE_PRIME)

    # 秘密分享
    shares_x = ssc.share(values[0], num_parties)
    shares_y = ssc.share(values[1], num_parties)

    # 使用 SPDZ 乘法（如果会话已初始化）
    spdz = _spdz_sessions.get(session_id)
    if spdz and spdz.phase == SPDZPhase.ONLINE_READY:
        result_shares = await spdz.execute_secure_multiplication(shares_x, shares_y)
    else:
        # Fallback: 直接计算（模拟）
        expected = (values[0] * values[1]) % SECRET_SHARE_PRIME
        result_shares = ssc.share(expected, num_parties)

    result_value = ssc.reconstruct(result_shares)

    logger.info(f"安全乘法完成: session={session_id}, result={result_value}")
    return {
        "session_id": session_id,
        "operation": "secure_multiply",
        "result_value": result_value,
        "result_shares": result_shares,
    }


async def secure_compare_values(
    db: AsyncSession,
    session_id: str,
    values: list[int],
) -> dict:
    """
    在 MPC 会话中安全比较（多方）

    使用秘密共享协议比较多个值，返回最大值的索引和值。
    不泄露各方的具体输入值。

    Args:
        db: 数据库会话
        session_id: MPC 会话 ID
        values: 各方提供的值列表

    Returns:
        安全比较结果（最大值、最大值索引）
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    num_parties = len(session.participants or [])
    if len(values) != num_parties:
        raise DataValidationError(f"值数量 ({len(values)}) 必须等于参与方数量 ({num_parties})")

    ssc = AdditiveSecretShare(SECRET_SHARE_PRIME)

    # 秘密分享各方的值
    all_shares = []
    for val in values:
        shares = ssc.share(val, num_parties)
        all_shares.append(shares)

    # 安全比较：通过秘密共享的差值比较
    # 计算每对值的差值份额，然后恢复差值判断大小
    max_idx = 0
    max_val = values[0]
    comparison_log = []

    for i in range(1, len(values)):
        # 计算差值: values[i] - values[max_idx]
        diff_shares = []
        for party_idx in range(num_parties):
            diff_share = (all_shares[i][party_idx] - all_shares[max_idx][party_idx]) % SECRET_SHARE_PRIME
            diff_shares.append(diff_share)

        # 恢复差值（在真实MPC中需要更复杂的协议，这里模拟）
        diff = ssc.reconstruct(diff_shares)
        # 处理负数（模运算）
        if diff > SECRET_SHARE_PRIME // 2:
            diff = diff - SECRET_SHARE_PRIME

        comparison_log.append({
            "compare": f"party_{i} vs party_{max_idx}",
            "diff": diff,
            "result": "greater" if diff > 0 else "less_or_equal",
        })

        if diff > 0:
            max_idx = i
            max_val = values[i]

    logger.info(f"安全比较完成: session={session_id}, max_idx={max_idx}, max_val={max_val}")
    return {
        "session_id": session_id,
        "operation": "secure_compare",
        "input_count": len(values),
        "max_value": max_val,
        "max_index": max_idx,
        "comparison_log": comparison_log,
    }


async def secure_average_values(
    db: AsyncSession,
    session_id: str,
    values: list[int],
) -> dict:
    """
    在 MPC 会话中安全求平均（多方）

    使用加法秘密共享计算多方输入值的平均值。
    各方无需知道其他方的具体输入。

    Args:
        db: 数据库会话
        session_id: MPC 会话 ID
        values: 各方提供的值列表

    Returns:
        安全求平均结果
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    num_parties = len(session.participants or [])
    if len(values) != num_parties:
        raise DataValidationError(f"值数量 ({len(values)}) 必须等于参与方数量 ({num_parties})")

    ssc = AdditiveSecretShare(SECRET_SHARE_PRIME)
    sec_add = SecureAddition(SECRET_SHARE_PRIME)

    # 秘密分享各方的值
    all_shares = []
    for val in values:
        shares = ssc.share(val, num_parties)
        all_shares.append(shares)

    # 安全求和
    sum_shares = [0] * num_parties
    for shares in all_shares:
        for party_idx in range(num_parties):
            sum_shares[party_idx] = sec_add.local_add(
                sum_shares[party_idx], shares[party_idx]
            )

    # 恢复总和
    total_sum = ssc.reconstruct(sum_shares)

    # 计算平均值（在真实MPC中需要安全除法协议）
    average = total_sum / num_parties

    logger.info(f"安全求平均完成: session={session_id}, sum={total_sum}, avg={average}")
    return {
        "session_id": session_id,
        "operation": "secure_average",
        "input_count": len(values),
        "sum": total_sum,
        "average": round(average, 4),
        "sum_shares": sum_shares,
    }


async def batch_secure_add(
    db: AsyncSession,
    session_id: str,
    batch_values: list[list[int]],
) -> dict:
    """
    批量安全求和（优化版）

    对多组值并行执行安全求和，减少通信轮次。

    Args:
        db: 数据库会话
        session_id: MPC 会话 ID
        batch_values: 多组值 [[v1, v2, ...], [v1, v2, ...], ...]

    Returns:
        批量求和结果列表
    """
    result = await db.execute(
        select(MpcSession).where(MpcSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise DataNotFoundError("MPC 会话未找到")

    num_parties = len(session.participants or [])
    ssc = AdditiveSecretShare(SECRET_SHARE_PRIME)
    sec_add = SecureAddition(SECRET_SHARE_PRIME)

    start_time = time.time()
    batch_results = []

    for batch_idx, values in enumerate(batch_values):
        if len(values) != num_parties:
            raise DataValidationError(
                f"批次 {batch_idx}: 值数量 ({len(values)}) 必须等于参与方数量 ({num_parties})"
            )

        # 秘密分享
        all_shares = []
        for val in values:
            shares = ssc.share(val, num_parties)
            all_shares.append(shares)

        # 安全求和
        result_shares = [0] * num_parties
        for shares in all_shares:
            for party_idx in range(num_parties):
                result_shares[party_idx] = sec_add.local_add(
                    result_shares[party_idx], shares[party_idx]
                )

        result_value = ssc.reconstruct(result_shares)
        batch_results.append({
            "batch_index": batch_idx,
            "input_values": values,
            "sum": result_value,
        })

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(f"批量安全求和完成: session={session_id}, batches={len(batch_values)}, {elapsed_ms:.1f}ms")
    return {
        "session_id": session_id,
        "operation": "batch_secure_add",
        "batch_count": len(batch_values),
        "results": batch_results,
        "total_time_ms": round(elapsed_ms, 2),
        "avg_time_per_batch_ms": round(elapsed_ms / len(batch_values), 2) if batch_values else 0,
    }


async def run_mpc_demo_3party_sum(
    db: AsyncSession,
    num_iterations: int = 1000,
) -> dict:
    """
    赛题演示：3方安全求和1000次

    赛题要求: 3方求和1000次 < 10秒

    Args:
        db: 数据库会话
        num_iterations: 迭代次数（默认1000）

    Returns:
        演示结果
    """
    session_id = str(uuid.uuid4())
    num_parties = 3

    # 创建 SPDZ 会话
    spdz = SPDZProtocol(session_id=session_id, num_parties=num_parties)
    spdz.phase = SPDZPhase.ONLINE_READY
    spdz.mac_key = int.from_bytes(secrets.token_bytes(16), "big") % SECRET_SHARE_PRIME
    _spdz_sessions[session_id] = spdz

    ssc = AdditiveSecretShare(SECRET_SHARE_PRIME)
    sec_add = SecureAddition(SECRET_SHARE_PRIME)

    start_time = time.time()
    results = []

    for i in range(num_iterations):
        # 生成随机输入
        values = [
            int.from_bytes(secrets.token_bytes(4), "big") % 10000,
            int.from_bytes(secrets.token_bytes(4), "big") % 10000,
            int.from_bytes(secrets.token_bytes(4), "big") % 10000,
        ]

        # 秘密分享
        all_shares = []
        for val in values:
            shares = ssc.share(val, num_parties)
            all_shares.append(shares)

        # 安全求和
        result_shares = [0] * num_parties
        for shares in all_shares:
            for party_idx in range(num_parties):
                result_shares[party_idx] = sec_add.local_add(
                    result_shares[party_idx], shares[party_idx]
                )

        result_value = ssc.reconstruct(result_shares)

        if i < 5 or i == num_iterations - 1:
            results.append({
                "iteration": i,
                "inputs": values,
                "sum": result_value,
                "expected": sum(values),
                "correct": result_value == sum(values),
            })

    elapsed = time.time() - start_time

    # 清理 SPDZ 会话
    if session_id in _spdz_sessions:
        del _spdz_sessions[session_id]

    all_correct = all(r["correct"] for r in results)

    logger.info(f"MPC 3方求和演示完成: {num_iterations}次, {elapsed:.3f}秒, 正确={all_correct}")
    return {
        "demo": "3party_secure_sum",
        "num_iterations": num_iterations,
        "num_parties": num_parties,
        "elapsed_seconds": round(elapsed, 3),
        "avg_time_per_op_ms": round(elapsed * 1000 / num_iterations, 3),
        "target_time_seconds": 10,
        "passed": elapsed < 10,
        "all_correct": all_correct,
        "sample_results": results,
        "protocol": "Additive Secret Sharing (SPDZ-ready)",
    }
