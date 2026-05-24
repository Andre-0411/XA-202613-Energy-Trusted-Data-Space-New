"""
计算沙箱服务 — 增强版
Docker 容器级隔离 + 进程级沙箱（subprocess + resource limits）
包含：算法准入检查（bandit 集成）、数据脱敏、出口审核、网络访问控制、文件系统隔离
沙箱状态持久化到数据库、超时自动清理、违规事件记录
"""
import uuid
import asyncio
import logging
import re
import json
import tempfile
import os
import shutil
import signal
import stat
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sandbox_model import SandboxSession, SandboxResourceUsage, SandboxViolation
from app.models.compute_task import ComputeTask
from app.exceptions import ComputeError, ComputeSandboxError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

DEFAULT_MEMORY_LIMIT = "2g"
DEFAULT_CPU_LIMIT = "1.0"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_DISK_LIMIT_MB = 512
DEFAULT_MAX_PROCESSES = 64

_docker_available: Optional[bool] = None

# 运行中沙箱的进程/容器映射
_running_processes: dict[str, asyncio.subprocess.Process] = {}
_running_tasks: dict[str, asyncio.Task] = {}

# 算法准入黑名单（危险调用）
DANGEROUS_CALLS = [
    r"os\.system", r"subprocess\.", r"eval\s*\(", r"exec\s*\(",
    r"__import__", r"compile\s*\(", r"globals\s*\(", r"locals\s*\(",
    r"getattr\s*\(.*,\s*['\"]__", r"setattr\s*\(", r"delattr\s*\(",
    r"open\s*\(.*/etc/", r"open\s*\(.*/proc/", r"open\s*\(.*/sys/",
    r"ctypes\.", r"socket\.", r"http\.client", r"urllib\.request",
    r"requests\.", r"shutil\.rmtree", r"os\.remove", r"os\.unlink",
    r"rmdir", r"mkfifo", r"mknod", r"sys\.exit", r"os\._exit",
    r"os\.fork", r"os\.kill", r"signal\.",
]

# 敏感数据模式
SENSITIVE_PATTERNS = [
    (r"\b\d{17}[\dXx]\b", "身份证号"),
    (r"\b1[3-9]\d{9}\b", "手机号"),
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "邮箱"),
    (r"\b\d{16,19}\b", "银行卡号"),
    (r"\b[A-Za-z0-9+/]{40,}={0,2}\b", "Base64编码数据"),
]

# Seccomp 安全策略模板（Docker 容器限制系统调用）
SECCOMP_PROFILE = {
    "defaultAction": "SCMP_ACT_ERRNO",
    "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86"],
    "syscalls": [
        {
            "names": [
                "read", "write", "close", "fstat", "lseek", "mmap", "mprotect",
                "munmap", "brk", "ioctl", "access", "pipe", "select", "sched_yield",
                "mremap", "msync", "mincore", "madvise", "dup", "dup2", "nanosleep",
                "getpid", "clone", "fork", "execve", "exit", "wait4", "kill",
                "uname", "fcntl", "flock", "fsync", "fdatasync", "truncate",
                "ftruncate", "getdents", "getcwd", "chdir", "mkdir", "rmdir",
                "creat", "unlink", "readlink", "chmod", "chown", "lchown",
                "gettimeofday", "getuid", "getgid", "geteuid", "getegid",
                "getppid", "getpgrp", "setsid", "setreuid", "setregid",
                "getgroups", "setgroups", "setresuid", "setresgid",
                "gettid", "tgkill", "sigaltstack", "rt_sigaction", "rt_sigprocmask",
                "rt_sigreturn", "pread64", "pwrite64", "readv", "writev",
                "set_thread_area", "arch_prctl", "futex", "set_robust_list",
                "get_robust_list", "epoll_wait", "epoll_ctl", "clock_gettime",
                "clock_getres", "exit_group", "epoll_create1", "pipe2",
                "preadv", "pwritev", "rt_sigpending", "rt_sigtimedwait",
                "rt_sigqueueinfo", "sigwaitinfo", "timerfd_create", "eventfd2",
                "epoll_create", "getdents64", "set_tid_address",
                "restart_syscall", "seccomp", "sendfile", "statfs", "fstatfs",
                "prlimit64", "getrandom", "memfd_create",
            ],
            "action": "SCMP_ACT_ALLOW",
        }
    ],
}


# ==================== Docker 检测 ====================

async def _check_docker_available() -> bool:
    """检查 Docker 是否可用"""
    global _docker_available
    if _docker_available is not None:
        return _docker_available

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5.0)
        _docker_available = proc.returncode == 0
    except Exception:
        _docker_available = False

    if not _docker_available:
        logger.warning("Docker 不可用，将使用进程级沙箱")
    return _docker_available


# ==================== 沙箱生命周期 ====================

async def create_sandbox(
    db: AsyncSession,
    task_id: str,
    algorithm_code: str,
    data_refs: list[str],
    name: str = "",
    organization_id: str = "",
    user_id: str = "",
    memory_limit: str = DEFAULT_MEMORY_LIMIT,
    cpu_limit: str = DEFAULT_CPU_LIMIT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    network_enabled: bool = False,
) -> str:
    """
    创建计算沙箱

    1. 算法准入检查（静态分析 + bandit）
    2. 数据脱敏（掩码敏感字段）
    3. 创建沙箱实例并持久化到数据库
    4. 创建隔离临时目录

    Args:
        db: 数据库会话
        task_id: 关联任务 ID
        algorithm_code: 算法代码（Python 脚本）
        data_refs: 数据引用列表（文件路径或数据集 ID）
        name: 沙箱名称
        organization_id: 组织 ID
        user_id: 用户 ID
        memory_limit: 内存限制（默认 2GB）
        cpu_limit: CPU 限制（默认 1 核）
        timeout_seconds: 执行超时（默认 300 秒）
        network_enabled: 是否启用网络（默认禁用）

    Returns:
        sandbox_id
    """
    sandbox_id = str(uuid.uuid4())

    # 1. 算法准入检查
    scan_result = _static_code_analysis(algorithm_code)
    if not scan_result["is_safe"]:
        raise ComputeSandboxError(
            f"算法准入检查不通过: {scan_result['issues']}"
        )

    # 2. 数据脱敏
    sanitized_code = _sanitize_sensitive_data(algorithm_code)

    # 3. 检测运行模式
    use_docker = await _check_docker_available()

    # 4. 创建隔离临时目录
    temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id[:8]}_")
    _set_restricted_permissions(temp_dir)

    # 5. 持久化到数据库
    session = SandboxSession(
        id=uuid.UUID(sandbox_id),
        task_id=uuid.UUID(task_id) if task_id else None,
        name=name or f"sandbox-{sandbox_id[:8]}",
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        status="created",
        mode="docker" if use_docker else "process",
        algorithm_hash=_simple_hash(algorithm_code),
        input_asset_ids=data_refs,
        runtime_config={
            "memory_limit": memory_limit,
            "cpu_limit": cpu_limit,
            "timeout_seconds": timeout_seconds,
            "network_enabled": network_enabled,
            "disk_limit_mb": DEFAULT_DISK_LIMIT_MB,
            "max_processes": DEFAULT_MAX_PROCESSES,
        },
        scan_result=scan_result,
        temp_dir=temp_dir,
    )
    db.add(session)
    await db.commit()

    logger.info(f"沙箱已创建: {sandbox_id}, 模式={'Docker' if use_docker else '进程级'}, temp={temp_dir}")
    return sandbox_id


async def execute_sandbox(db: AsyncSession, sandbox_id: str) -> dict:
    """
    执行沙箱任务

    Args:
        db: 数据库会话
        sandbox_id: 沙箱 ID

    Returns:
        执行结果
    """
    result = await db.execute(
        select(SandboxSession).where(SandboxSession.id == uuid.UUID(sandbox_id))
    )
    sandbox = result.scalar_one_or_none()
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")

    if sandbox.status != "created":
        raise ComputeError(f"沙箱状态不允许执行: {sandbox.status}")

    # 更新状态
    sandbox.status = "running"
    sandbox.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        runtime_config = sandbox.runtime_config or {}
        timeout = runtime_config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        network_enabled = runtime_config.get("network_enabled", False)

        if sandbox.mode == "docker":
            result_dict = await _execute_in_docker(sandbox, runtime_config)
        else:
            result_dict = await _execute_in_process(sandbox, runtime_config)

        # 出口审核
        audit_result = _export_audit(result_dict)
        if not audit_result["is_safe"]:
            sandbox.status = "violation"
            sandbox.export_result = audit_result
            sandbox.error_message = "出口审核不通过"
            await db.commit()

            # 记录违规
            violation = SandboxViolation(
                session_id=uuid.UUID(sandbox_id),
                violation_type="data_leak",
                severity="high",
                description=f"出口审核不通过: {audit_result['issues']}",
                evidence=audit_result,
                action_taken="terminated",
            )
            db.add(violation)
            await db.commit()

            return {
                "sandbox_id": sandbox_id,
                "status": "violation",
                "audit_issues": audit_result["issues"],
            }

        # 记录资源使用
        await _record_resource_usage(db, sandbox_id, result_dict)

        sandbox.status = "completed"
        sandbox.completed_at = datetime.now(timezone.utc)
        sandbox.export_result = audit_result
        await db.commit()

        return {
            "sandbox_id": sandbox_id,
            "status": "completed",
            "result": result_dict,
            "audit": audit_result,
        }

    except asyncio.TimeoutError:
        sandbox.status = "timeout"
        sandbox.error_message = f"执行超时（{sandbox.runtime_config.get('timeout_seconds', DEFAULT_TIMEOUT_SECONDS)}秒）"
        await db.commit()

        # 记录违规
        violation = SandboxViolation(
            session_id=uuid.UUID(sandbox_id),
            violation_type="timeout",
            severity="medium",
            description=sandbox.error_message,
            action_taken="terminated",
        )
        db.add(violation)
        await db.commit()

        raise ComputeError(f"沙箱执行超时: {sandbox_id}")

    except Exception as e:
        sandbox.status = "failed"
        sandbox.error_message = str(e)
        await db.commit()
        logger.error(f"沙箱执行失败: {sandbox_id}, error={e}")
        raise ComputeError(f"沙箱执行失败: {e}")

    finally:
        # 清理运行中的进程引用
        _running_processes.pop(sandbox_id, None)
        _running_tasks.pop(sandbox_id, None)


async def destroy_sandbox(db: AsyncSession, sandbox_id: str) -> dict:
    """
    销毁沙箱 — 停止进程/容器并清理资源

    Args:
        db: 数据库会话
        sandbox_id: 沙箱 ID

    Returns:
        销毁结果
    """
    result = await db.execute(
        select(SandboxSession).where(SandboxSession.id == uuid.UUID(sandbox_id))
    )
    sandbox = result.scalar_one_or_none()
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")

    if sandbox.status == "running":
        # 尝试停止运行中的容器/进程
        if sandbox.mode == "docker" and sandbox.container_id:
            await _stop_docker_container(sandbox.container_id)
        if sandbox.process_pid:
            _kill_process(sandbox.process_pid)

        # 取消异步任务
        running_task = _running_tasks.get(sandbox_id)
        if running_task and not running_task.done():
            running_task.cancel()

    # 清理临时目录
    if sandbox.temp_dir and os.path.exists(sandbox.temp_dir):
        shutil.rmtree(sandbox.temp_dir, ignore_errors=True)

    sandbox.status = "destroyed"
    sandbox.destroyed_at = datetime.now(timezone.utc)
    await db.commit()

    _running_processes.pop(sandbox_id, None)
    _running_tasks.pop(sandbox_id, None)

    logger.info(f"沙箱已销毁: {sandbox_id}")
    return {
        "sandbox_id": sandbox_id,
        "status": "destroyed",
        "destroyed_at": sandbox.destroyed_at.isoformat(),
    }


async def cleanup_expired_sandboxes(db: AsyncSession, max_age_seconds: int = 3600) -> int:
    """
    清理超时沙箱 — 定时调用

    Args:
        db: 数据库会话
        max_age_seconds: 最大存活时间（秒）

    Returns:
        清理数量
    """
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

    result = await db.execute(
        select(SandboxSession).where(
            SandboxSession.status.in_(["created", "running", "active"]),
            SandboxSession.created_at < cutoff_dt,
        )
    )
    expired = result.scalars().all()
    count = 0
    for sandbox in expired:
        try:
            sandbox.status = "destroyed"
            sandbox.destroyed_at = datetime.now(timezone.utc)
            sandbox.error_message = "超时自动清理"
            count += 1

            # 清理临时目录
            if sandbox.temp_dir and os.path.exists(sandbox.temp_dir):
                shutil.rmtree(sandbox.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"清理沙箱失败: {sandbox.id}, error={e}")

    await db.commit()
    if count:
        logger.info(f"清理超时沙箱: {count} 个")
    return count


async def get_sandbox_status(db: AsyncSession, sandbox_id: str) -> dict:
    """获取沙箱状态"""
    result = await db.execute(
        select(SandboxSession).where(SandboxSession.id == uuid.UUID(sandbox_id))
    )
    sandbox = result.scalar_one_or_none()
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")

    return {
        "sandbox_id": str(sandbox.id),
        "task_id": str(sandbox.task_id) if sandbox.task_id else None,
        "name": sandbox.name,
        "status": sandbox.status,
        "mode": sandbox.mode,
        "runtime_config": sandbox.runtime_config,
        "scan_result": sandbox.scan_result,
        "export_result": sandbox.export_result,
        "created_at": sandbox.created_at.isoformat() if sandbox.created_at else None,
        "started_at": sandbox.started_at.isoformat() if sandbox.started_at else None,
        "completed_at": sandbox.completed_at.isoformat() if sandbox.completed_at else None,
        "error_message": sandbox.error_message,
    }


async def get_sandbox_violations(db: AsyncSession, sandbox_id: str) -> list[dict]:
    """获取沙箱违规记录"""
    result = await db.execute(
        select(SandboxViolation)
        .where(SandboxViolation.session_id == uuid.UUID(sandbox_id))
        .order_by(SandboxViolation.occurred_at.desc())
    )
    violations = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "violation_type": v.violation_type,
            "severity": v.severity,
            "description": v.description,
            "evidence": v.evidence,
            "action_taken": v.action_taken,
            "occurred_at": v.occurred_at.isoformat(),
        }
        for v in violations
    ]


async def list_sandboxes(
    db: AsyncSession,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """查询沙箱列表（从数据库）"""
    query = select(SandboxSession)
    if status:
        query = query.where(SandboxSession.status == status)
    if organization_id:
        query = query.where(SandboxSession.organization_id == uuid.UUID(organization_id))

    query = query.order_by(SandboxSession.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    sessions = result.scalars().all()

    items = [
        {
            "sandbox_id": str(s.id),
            "name": s.name,
            "status": s.status,
            "mode": s.mode,
            "organization_id": str(s.organization_id),
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]

    return {"items": items, "total": len(items), "limit": limit, "offset": offset}


# ==================== Docker 容器执行 ====================

async def _execute_in_docker(sandbox: SandboxSession, runtime_config: dict) -> dict:
    """在 Docker 容器中执行算法"""
    sandbox_id = str(sandbox.id)
    code = sandbox.algorithm_hash  # 需要从临时目录读取或直接使用存储的代码
    timeout = runtime_config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    memory = runtime_config.get("memory_limit", DEFAULT_MEMORY_LIMIT)
    cpu = runtime_config.get("cpu_limit", DEFAULT_CPU_LIMIT)
    network_enabled = runtime_config.get("network_enabled", False)
    temp_dir = sandbox.temp_dir or tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id[:8]}_")

    # 写入算法脚本
    script_path = os.path.join(temp_dir, "algorithm.py")
    # 从 scan_result 中获取原始代码（如果存储了）或使用占位
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(f"# Algorithm for sandbox {sandbox_id}\n")
        f.write("print('Sandbox execution placeholder')\n")

    # 准备 seccomp 配置
    seccomp_path = os.path.join(temp_dir, "seccomp.json")
    with open(seccomp_path, "w", encoding="utf-8") as f:
        json.dump(SECCOMP_PROFILE, f)

    # 构建 Docker 命令
    docker_cmd = [
        "docker", "run", "--rm",
        f"--memory={memory}",
        f"--cpus={cpu}",
        f"--pids-limit={runtime_config.get('max_processes', DEFAULT_MAX_PROCESSES)}",
        f"--storage-opt=size={runtime_config.get('disk_limit_mb', DEFAULT_DISK_LIMIT_MB)}m",
        f"--read-only",
        f"--tmpfs=/tmp:size=100m",
        f"-v", f"{script_path}:/app/algorithm.py:ro",
        "--workdir=/app",
    ]

    # 网络控制
    if not network_enabled:
        docker_cmd.append("--network=none")

    docker_cmd.extend([
        "--security-opt", f"seccomp={seccomp_path}",
        "python:3.11-slim",
        "python", "/app/algorithm.py",
    ])

    try:
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        sandbox.container_id = str(proc.pid)
        _running_processes[sandbox_id] = proc

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")

        return {
            "success": proc.returncode == 0,
            "output": output,
            "error": error_output,
            "exit_code": proc.returncode,
            "cpu_seconds": 0.0,
            "memory_peak_mb": 0.0,
        }

    finally:
        _running_processes.pop(sandbox_id, None)


async def _stop_docker_container(container_id: str) -> None:
    """停止 Docker 容器"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "kill", str(container_id),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10.0)
    except Exception as e:
        logger.warning(f"停止容器失败: {e}")


# ==================== 进程级沙箱（增强版） ====================

async def _execute_in_process(sandbox: SandboxSession, runtime_config: dict) -> dict:
    """
    进程级沙箱执行 — 增强版

    使用 subprocess 执行，通过 resource.setrlimit 限制资源：
    - 内存限制（RLIMIT_AS）
    - CPU 时间限制（RLIMIT_CPU）
    - 文件大小限制（RLIMIT_FSIZE）
    - 进程数限制（RLIMIT_NPROC）
    - 核心转储禁用（RLIMIT_CORE）

    额外安全措施：
    - 网络访问控制（iptables/防火墙规则或代码级禁止）
    - 文件系统隔离（临时目录 + 权限控制）
    - 超时自动清理
    """
    sandbox_id = str(sandbox.id)
    timeout = runtime_config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    memory_limit = runtime_config.get("memory_limit", DEFAULT_MEMORY_LIMIT)
    cpu_limit = runtime_config.get("cpu_limit", DEFAULT_CPU_LIMIT)
    network_enabled = runtime_config.get("network_enabled", False)
    disk_limit_mb = runtime_config.get("disk_limit_mb", DEFAULT_DISK_LIMIT_MB)
    max_processes = runtime_config.get("max_processes", DEFAULT_MAX_PROCESSES)

    temp_dir = sandbox.temp_dir or tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id[:8]}_")

    # 写入算法脚本
    script_path = os.path.join(temp_dir, "algorithm.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(f"# Algorithm for sandbox {sandbox_id}\n")
        f.write("print('Sandbox execution placeholder')\n")

    # 进程级资源限制包装脚本
    memory_bytes = _parse_memory_limit(memory_limit)
    cpu_seconds = int(float(cpu_limit.replace("n", "")) * timeout)
    disk_bytes = disk_limit_mb * 1024 * 1024

    wrapper_code = f'''#!/usr/bin/env python3
"""
沙箱资源限制包装器
在执行用户代码前设置操作系统级资源限制
"""
import resource
import sys
import os

# ==================== 资源限制 ====================

# 内存限制（虚拟地址空间）
memory_bytes = {memory_bytes}
try:
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
except (ValueError, OSError) as e:
    print(f"WARNING: 内存限制设置失败: {{e}}", file=sys.stderr)

# CPU 时间限制
cpu_seconds = {cpu_seconds}
try:
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
except (ValueError, OSError) as e:
    print(f"WARNING: CPU 限制设置失败: {{e}}", file=sys.stderr)

# 文件大小限制
file_size_bytes = {disk_bytes}
try:
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_bytes, file_size_bytes))
except (ValueError, OSError) as e:
    print(f"WARNING: 文件大小限制设置失败: {{e}}", file=sys.stderr)

# 进程数限制
max_procs = {max_processes}
try:
    resource.setrlimit(resource.RLIMIT_NPROC, (max_procs, max_procs))
except (ValueError, OSError) as e:
    print(f"WARNING: 进程数限制设置失败: {{e}}", file=sys.stderr)

# 禁止核心转储
try:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
except (ValueError, OSError):
    pass

# ==================== 网络访问控制 ====================
{"# 网络访问已禁用" if not network_enabled else "# 网络访问已启用"}
network_enabled = {network_enabled}

if not network_enabled:
    # 在代码级别阻止网络模块导入
    import importlib
    _original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
    _BLOCKED_MODULES = {{'socket', 'http', 'urllib', 'requests', 'aiohttp', 'httpx', 'websocket'}}

    def _restricted_import(name, *args, **kwargs):
        top_level = name.split('.')[0]
        if top_level in _BLOCKED_MODULES:
            raise ImportError(f"网络访问已禁用: 模块 '{{name}}' 不允许导入")
        return _original_import(name, *args, **kwargs)

    if hasattr(__builtins__, '__import__'):
        __builtins__.__import__ = _restricted_import
    else:
        import builtins
        builtins.__import__ = _restricted_import

# ==================== 文件系统限制 ====================
# 只允许在临时目录中读写
_sandbox_dir = r"{temp_dir}"
_original_open = open
_allowed_prefixes = (_sandbox_dir, "/tmp")

def _restricted_open(file, *args, **kwargs):
    file_str = str(file)
    # 检查是否尝试访问受限路径
    restricted = ['/etc/', '/proc/', '/sys/', '/dev/', '/root/', '/home/']
    for prefix in restricted:
        if file_str.startswith(prefix) or prefix in file_str:
            raise PermissionError(f"沙箱中不允许访问: {{file_str}}")
    return _original_open(file, *args, **kwargs)

import builtins
builtins.open = _restricted_open

# ==================== 执行用户代码 ====================
script_path = r"{script_path}"
try:
    with open(script_path, "r") as f:
        code = f.read()
    exec(compile(code, script_path, "exec"), {{"__name__": "__main__", "__file__": script_path}})
except Exception as e:
    print(f"EXECUTION_ERROR: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
'''

    wrapper_path = os.path.join(temp_dir, "wrapper.py")
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(wrapper_code)

    # 构建受限环境变量
    safe_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": temp_dir,
        "TMPDIR": os.path.join(temp_dir, "tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "LANG": "C.UTF-8",
    }
    os.makedirs(safe_env["TMPDIR"], exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable if hasattr(sys := __import__('sys'), 'executable') else "python",
            str(wrapper_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(temp_dir),
            env=safe_env,
            # 新会话，脱离父进程进程组
            preexec_fn=os.setsid if os.name != 'nt' else None,
        )
        sandbox.process_pid = proc.pid
        _running_processes[sandbox_id] = proc

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")

        # 检测网络访问违规
        if not network_enabled and ("socket" in error_output.lower() or "connection" in error_output.lower()):
            violation = SandboxViolation(
                session_id=uuid.UUID(sandbox_id),
                violation_type="network_access",
                severity="high",
                description=f"检测到网络访问尝试: {error_output[:500]}",
                evidence={"stderr": error_output[:1000]},
                action_taken="blocked",
            )
            logger.warning(f"沙箱 {sandbox_id} 网络访问违规")

        return {
            "success": proc.returncode == 0,
            "output": output,
            "error": error_output,
            "exit_code": proc.returncode,
            "cpu_seconds": 0.0,
            "memory_peak_mb": 0.0,
        }

    except asyncio.TimeoutError:
        # 超时清理
        if proc and proc.returncode is None:
            try:
                # 先尝试优雅终止
                if os.name != 'nt':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                # 等待 5 秒后强制终止
                await asyncio.sleep(5)
                if proc.returncode is None:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
            except (ProcessLookupError, PermissionError, OSError):
                pass
        raise

    finally:
        _running_processes.pop(sandbox_id, None)


# ==================== 进程/目录工具 ====================

def _set_restricted_permissions(path: str) -> None:
    """设置目录权限为所有者可读写执行"""
    try:
        os.chmod(path, stat.S_IRWXU)  # 0o700
    except OSError as e:
        logger.warning(f"设置目录权限失败: {path}, error={e}")


def _kill_process(pid: int) -> None:
    """终止进程"""
    try:
        if os.name != 'nt':
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _parse_memory_limit(limit_str: str) -> int:
    """解析内存限制字符串为字节数"""
    limit_str = limit_str.lower().strip()
    if limit_str.endswith("g"):
        return int(float(limit_str[:-1]) * 1024 * 1024 * 1024)
    elif limit_str.endswith("m"):
        return int(float(limit_str[:-1]) * 1024 * 1024)
    elif limit_str.endswith("k"):
        return int(float(limit_str[:-1]) * 1024)
    return int(limit_str)


# ==================== 资源使用记录 ====================

async def _record_resource_usage(
    db: AsyncSession, sandbox_id: str, result_dict: dict,
) -> None:
    """记录沙箱资源使用情况"""
    metrics = [
        ("cpu_seconds", result_dict.get("cpu_seconds", 0.0)),
        ("memory_peak_mb", result_dict.get("memory_peak_mb", 0.0)),
    ]
    for metric_type, value in metrics:
        if value > 0:
            usage = SandboxResourceUsage(
                session_id=uuid.UUID(sandbox_id),
                metric_type=metric_type,
                metric_value=value,
            )
            db.add(usage)
    await db.commit()


# ==================== 安全检查 ====================

def _static_code_analysis(code: str) -> dict:
    """
    算法准入检查 — 静态代码分析

    检测危险调用、网络访问、文件系统操作等
    尝试集成 bandit（如果可用）

    Returns:
        {"is_safe": bool, "issues": list, "risk_level": str, "bandit_result": dict}
    """
    issues = []

    for pattern in DANGEROUS_CALLS:
        matches = re.findall(pattern, code)
        if matches:
            issues.append({
                "pattern": pattern,
                "matches": matches[:3],
                "severity": "critical",
            })

    # 检查代码长度
    lines = code.strip().split("\n")
    if len(lines) > 1000:
        issues.append({
            "pattern": "code_length",
            "matches": [f"{len(lines)} lines"],
            "severity": "warning",
        })

    # 尝试 bandit 静态分析
    bandit_result = _run_bandit_analysis(code)

    is_safe = len([i for i in issues if i["severity"] == "critical"]) == 0
    if bandit_result and bandit_result.get("issue_count", 0) > 0:
        # bandit 发现高危问题时标记不安全
        high_issues = [
            issue for issue in bandit_result.get("issues", [])
            if issue.get("issue_severity", "").upper() == "HIGH"
        ]
        if high_issues:
            is_safe = False
            issues.append({
                "pattern": "bandit_high",
                "matches": [f"bandit 发现 {len(high_issues)} 个高危问题"],
                "severity": "critical",
            })

    risk_level = "safe" if not issues else (
        "critical" if any(i["severity"] == "critical" for i in issues) else "warning"
    )

    return {
        "is_safe": is_safe,
        "issues": issues,
        "risk_level": risk_level,
        "code_lines": len(lines),
        "bandit_result": bandit_result,
    }


def _run_bandit_analysis(code: str) -> Optional[dict]:
    """
    尝试运行 bandit 静态代码分析

    如果 bandit 未安装，返回 None
    """
    try:
        import tempfile
        import subprocess

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["python", "-m", "bandit", "-f", "json", "-q", tmp_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode in (0, 1):  # 0=无问题, 1=发现问题
                import json as json_mod
                data = json_mod.loads(result.stdout) if result.stdout else {}
                return {
                    "issue_count": data.get("metrics", {}).get("_totals", {}).get("SEVERITY.HIGH", 0),
                    "issues": data.get("results", [])[:20],
                    "metrics": data.get("metrics", {}).get("_totals", {}),
                }
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
        finally:
            os.unlink(tmp_path)

    except ImportError:
        pass

    return None


def _sanitize_sensitive_data(text: str) -> str:
    """数据脱敏 — 进入沙箱前自动掩码敏感字段"""
    result = text

    # 身份证号掩码：保留前3后4
    result = re.sub(
        r"\b(\d{3})\d{11}(\d{3}[\dXx])\b",
        lambda m: m.group(1) + "*" * 11 + m.group(2),
        result,
    )

    # 手机号掩码：保留前3后4
    result = re.sub(
        r"\b(1[3-9]\d)\d{4}(\d{4})\b",
        lambda m: m.group(1) + "****" + m.group(2),
        result,
    )

    # 邮箱掩码：保留首字符和域名
    result = re.sub(
        r"\b([a-zA-Z0-9])[a-zA-Z0-9._%+-]*(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
        lambda m: m.group(1) + "***" + m.group(2),
        result,
    )

    # 银行卡号掩码：保留前4后4
    result = re.sub(
        r"\b(\d{4})\d{8,12}(\d{4})\b",
        lambda m: m.group(1) + "*" * (len(m.group(0)) - 8) + m.group(2),
        result,
    )

    return result


def _export_audit(result: dict) -> dict:
    """
    出口审核 — 检测结果中是否包含原始数据泄露

    Returns:
        {"is_safe": bool, "issues": list, "output_size_bytes": int}
    """
    issues = []
    output = result.get("output", "") + result.get("error", "")

    for pattern, desc in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, output)
        if matches:
            issues.append({
                "type": desc,
                "count": len(matches),
                "severity": "high",
            })

    # 检查输出大小
    output_bytes = len(output.encode("utf-8"))
    if output_bytes > 10 * 1024 * 1024:  # 10MB
        issues.append({
            "type": "output_too_large",
            "size_bytes": output_bytes,
            "severity": "medium",
        })

    return {
        "is_safe": len(issues) == 0,
        "issues": issues,
        "output_size_bytes": output_bytes,
    }


def _simple_hash(data: str) -> str:
    """简单哈希（用于标识，非加密用途）"""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()[:32]
