"""可信共享中心 - 业务逻辑层"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import ComputeTask, DataAsset, User
from app.schemas.compute import TaskCreate, TaskResult as TaskResultSchema
from .privacy import (
    simulate_fl_task,
    simulate_mpc_task,
    simulate_tee_task,
    simulate_he_task,
    get_task_estimate,
)

# 任务类型与模拟函数映射
_TASK_SIMULATORS = {
    "FL": simulate_fl_task,
    "MPC": simulate_mpc_task,
    "TEE": simulate_tee_task,
    "HE": simulate_he_task,
}


def create_task(db: Session, user_id: int, task_in: TaskCreate) -> ComputeTask:
    """创建计算任务，验证输入资产是否存在且已发布"""
    # 验证输入资产
    input_assets = task_in.config.input_assets
    if input_assets:
        assets = db.query(DataAsset).filter(
            DataAsset.id.in_(input_assets),
            DataAsset.status == "published",
        ).all()
        found_ids = {a.id for a in assets}
        missing = set(input_assets) - found_ids
        if missing:
            raise ValueError(f"数据资产不存在或未发布: {missing}")

    task = ComputeTask(
        name=task_in.name,
        description=task_in.description,
        task_type=task_in.task_type.upper(),
        status="created",
        config=task_in.config.model_dump(),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def start_task(db: Session, task_id: int, user_id: int) -> ComputeTask:
    """启动任务，验证用户是创建者，设置状态并模拟执行"""
    task = db.query(ComputeTask).filter(ComputeTask.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    if task.created_by != user_id:
        raise ValueError("无权操作此任务")
    if task.status not in ("created", "failed"):
        raise ValueError(f"当前状态({task.status})不允许启动")

    task.status = "running"
    task.progress = 50
    task.started_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    # Demo: 立即模拟完成
    _execute_task_sync(db, task)
    db.refresh(task)
    return task


def cancel_task(db: Session, task_id: int, user_id: int) -> ComputeTask:
    """取消任务，仅 created/queued 状态可取消"""
    task = db.query(ComputeTask).filter(ComputeTask.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    if task.created_by != user_id:
        raise ValueError("无权操作此任务")
    if task.status not in ("created", "queued"):
        raise ValueError(f"当前状态({task.status})不允许取消")

    task.status = "cancelled"
    task.progress = 0
    db.commit()
    db.refresh(task)
    return task


def retry_task(db: Session, task_id: int, user_id: int) -> ComputeTask:
    """重试失败任务，重置状态为 created"""
    task = db.query(ComputeTask).filter(ComputeTask.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    if task.created_by != user_id:
        raise ValueError("无权操作此任务")
    if task.status != "failed":
        raise ValueError("仅失败任务可重试")

    task.status = "created"
    task.progress = 0
    task.error_message = None
    task.result = None
    task.started_at = None
    task.finished_at = None
    db.commit()
    db.refresh(task)
    return task


def get_task_result(db: Session, task_id: int, user_id: int) -> TaskResultSchema:
    """获取任务结果详情"""
    task = db.query(ComputeTask).filter(ComputeTask.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    if task.created_by != user_id:
        raise ValueError("无权查看此任务")

    summary = None
    if task.result:
        summary = _build_summary(task)

    return TaskResultSchema(
        task_id=task.id,
        task_name=task.name,
        task_type=task.task_type,
        status=task.status,
        result=task.result,
        summary=summary,
    )


def get_task_list(
    db: Session,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    created_by: Optional[int] = None,
) -> tuple[List[ComputeTask], int]:
    """获取任务列表，支持分页和筛选"""
    query = db.query(ComputeTask)

    if status:
        query = query.filter(ComputeTask.status == status)
    if task_type:
        query = query.filter(ComputeTask.task_type == task_type.upper())
    if created_by:
        query = query.filter(ComputeTask.created_by == created_by)

    total = query.count()
    tasks = query.order_by(ComputeTask.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return tasks, total


def get_task_detail(db: Session, task_id: int) -> Optional[Dict[str, Any]]:
    """获取任务详情（含创建者名称）"""
    task = db.query(ComputeTask).filter(ComputeTask.id == task_id).first()
    if not task:
        return None

    creator = db.query(User).filter(User.id == task.created_by).first()
    creator_name = creator.real_name if creator and creator.real_name else (
        creator.username if creator else None
    )

    result = {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "task_type": task.task_type,
        "status": task.status,
        "config": task.config,
        "result": task.result,
        "error_message": task.error_message,
        "progress": task.progress,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "created_by": task.created_by,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "creator_name": creator_name,
    }
    return result


def _execute_task_sync(db: Session, task: ComputeTask) -> None:
    """内部方法：根据任务类型调用对应的模拟函数，更新任务结果"""
    simulator = _TASK_SIMULATORS.get(task.task_type)
    if not simulator:
        task.status = "failed"
        task.error_message = f"不支持的任务类型: {task.task_type}"
        task.finished_at = datetime.utcnow()
        db.commit()
        return

    try:
        result = simulator(task.config or {})
        task.result = result
        task.progress = 100
        task.status = "completed"
        task.finished_at = datetime.utcnow()
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.finished_at = datetime.utcnow()

    db.commit()


def _build_summary(task: ComputeTask) -> Dict[str, Any]:
    """根据任务类型构建结果摘要"""
    result = task.result or {}
    task_type = task.task_type

    if task_type == "FL":
        return {
            "algorithm": result.get("algorithm"),
            "participants_count": len(result.get("participants", [])),
            "rounds": result.get("rounds"),
            "final_accuracy": result.get("final_accuracy"),
            "final_loss": result.get("final_loss"),
            "execution_time_seconds": result.get("execution_time_seconds"),
            "privacy_budget_used": result.get("privacy_budget_used"),
        }
    elif task_type == "MPC":
        return {
            "protocol": result.get("protocol"),
            "computation_type": result.get("computation_type"),
            "parties_count": len(result.get("parties", [])),
            "communication_rounds": result.get("communication_rounds"),
            "execution_time_seconds": result.get("execution_time_seconds"),
        }
    elif task_type == "TEE":
        return {
            "enclave_type": result.get("enclave_type"),
            "attestation_status": result.get("attestation_status"),
            "security_level": result.get("security_level"),
            "execution_time_seconds": result.get("execution_time_seconds"),
        }
    elif task_type == "HE":
        return {
            "scheme": result.get("scheme"),
            "operation_type": result.get("operation_type"),
            "precision_bits": result.get("precision_bits"),
            "execution_time_seconds": result.get("execution_time_seconds"),
            "noise_budget_remaining": result.get("noise_budget_remaining"),
        }
    return {"message": "结果摘要不可用"}
