from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, cast, Date

from app.models import SystemStat, User, Organization, DataAsset, ComputeTask, EvidenceRecord, AuthToken, AuditLog
from app.schemas.analytics import AnalyticsOverview, TrendResponse, StatPoint, StatSeries


def get_analytics_overview(db: Session) -> AnalyticsOverview:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_organizations = db.query(func.count(Organization.id)).scalar() or 0
    total_assets = db.query(func.count(DataAsset.id)).scalar() or 0
    total_compute_tasks = db.query(func.count(ComputeTask.id)).scalar() or 0
    total_evidence_records = db.query(func.count(EvidenceRecord.id)).scalar() or 0
    total_auth_tokens = db.query(func.count(AuthToken.id)).scalar() or 0

    completed_tasks = db.query(func.count(ComputeTask.id)).filter(ComputeTask.status == "completed").scalar() or 0
    task_completion_rate = round(completed_tasks / total_compute_tasks * 100, 1) if total_compute_tasks > 0 else 0.0

    avg_duration = None
    if completed_tasks > 0:
        result = db.query(func.avg(
            func.extract('epoch', ComputeTask.finished_at) - func.extract('epoch', ComputeTask.started_at)
        )).filter(ComputeTask.status == "completed", ComputeTask.finished_at.isnot(None), ComputeTask.started_at.isnot(None)).scalar()
        if result is not None:
            avg_duration = round(float(result), 1)

    return AnalyticsOverview(
        total_users=total_users,
        total_organizations=total_organizations,
        total_assets=total_assets,
        total_compute_tasks=total_compute_tasks,
        total_evidence_records=total_evidence_records,
        total_auth_tokens=total_auth_tokens,
        task_completion_rate=task_completion_rate,
        avg_task_duration=avg_duration,
    )


def get_trend_data(
    db: Session,
    metric_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = "day",
) -> TrendResponse:
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    query = db.query(
        SystemStat.stat_date,
        SystemStat.metric_value,
    ).filter(
        SystemStat.metric_name == metric_name,
        SystemStat.stat_date >= start_date,
        SystemStat.stat_date <= end_date,
        SystemStat.dimension == "all",
    ).order_by(SystemStat.stat_date).all()

    raw_data = {r[0]: float(r[1]) for r in query}

    if granularity == "week":
        data = _aggregate_weekly(raw_data, start_date, end_date)
    elif granularity == "month":
        data = _aggregate_monthly(raw_data, start_date, end_date)
    else:
        data = _fill_daily(raw_data, start_date, end_date)

    return TrendResponse(
        metric_name=metric_name,
        granularity=granularity,
        data=data,
    )


def get_multi_trend(
    db: Session,
    metric_names: List[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = "day",
) -> List[StatSeries]:
    results = []
    for metric_name in metric_names:
        trend = get_trend_data(db, metric_name, start_date, end_date, granularity)
        results.append(StatSeries(
            metric_name=metric_name,
            data=trend.data,
        ))
    return results


def get_top_resources(db: Session, resource_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    query = db.query(
        AuditLog.resource_type,
        AuditLog.resource_id,
        func.count(AuditLog.id).label("access_count"),
    ).filter(AuditLog.status == "success")

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    results = query.group_by(AuditLog.resource_type, AuditLog.resource_id).order_by(
        func.count(AuditLog.id).desc()
    ).limit(limit).all()

    return [{"resource_type": r[0], "resource_id": r[1], "access_count": r[2]} for r in results]


def get_user_activity(db: Session, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
    since = datetime.utcnow() - timedelta(days=days)
    results = db.query(
        User.id,
        User.username,
        User.real_name,
        func.count(AuditLog.id).label("activity_count"),
    ).join(AuditLog, AuditLog.user_id == User.id).filter(
        AuditLog.timestamp >= since,
    ).group_by(User.id, User.username, User.real_name).order_by(
        func.count(AuditLog.id).desc()
    ).limit(limit).all()

    return [{"user_id": r[0], "username": r[1], "real_name": r[2], "activity_count": r[3]} for r in results]


def get_asset_statistics(db: Session) -> Dict[str, Any]:
    by_type = db.query(DataAsset.asset_type, func.count(DataAsset.id)).group_by(DataAsset.asset_type).all()
    by_category = db.query(DataAsset.category, func.count(DataAsset.id)).group_by(DataAsset.category).all()
    by_status = db.query(DataAsset.status, func.count(DataAsset.id)).group_by(DataAsset.status).all()

    return {
        "by_type": {r[0]: r[1] for r in by_type},
        "by_category": {r[0]: r[1] for r in by_category if r[0]},
        "by_status": {r[0]: r[1] for r in by_status},
        "total": sum(r[1] for r in by_type),
    }


def get_task_statistics(db: Session) -> Dict[str, Any]:
    by_type = db.query(ComputeTask.task_type, func.count(ComputeTask.id)).group_by(ComputeTask.task_type).all()
    by_status = db.query(ComputeTask.status, func.count(ComputeTask.id)).group_by(ComputeTask.status).all()

    return {
        "by_type": {r[0]: r[1] for r in by_type},
        "by_status": {r[0]: r[1] for r in by_status},
        "total": sum(r[1] for r in by_type),
    }


def _fill_daily(raw_data: dict, start_date: date, end_date: date) -> List[StatPoint]:
    points = []
    current = start_date
    while current <= end_date:
        points.append(StatPoint(
            date=current.isoformat(),
            value=raw_data.get(current, 0),
        ))
        current += timedelta(days=1)
    return points


def _aggregate_weekly(raw_data: dict, start_date: date, end_date: date) -> List[StatPoint]:
    points = []
    current = start_date
    while current <= end_date:
        week_end = min(current + timedelta(days=6), end_date)
        week_sum = sum(raw_data.get(current + timedelta(days=d), 0) for d in range((week_end - current).days + 1))
        points.append(StatPoint(
            date=current.isoformat(),
            value=round(week_sum / 7, 1),
        ))
        current = week_end + timedelta(days=1)
    return points


def _aggregate_monthly(raw_data: dict, start_date: date, end_date: date) -> List[StatPoint]:
    monthly: Dict[str, float] = {}
    current = start_date
    while current <= end_date:
        key = current.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + raw_data.get(current, 0)
        current += timedelta(days=1)
    return [StatPoint(date=k, value=round(v, 1)) for k, v in sorted(monthly.items())]
