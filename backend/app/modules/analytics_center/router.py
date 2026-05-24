"""
Analytics Center Router Module.

This module provides API endpoints for analytics and AI chat.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.utils.deps import get_current_user, require_role
from app.models import User
from app.schemas.analytics import (
    AnalyticsOverview,
    TrendRequest,
    TrendResponse,
    StatSeries,
    AIChatRequest,
    AIChatResponse,
    AIChatMessage
)
from app.schemas import PaginatedResponse, PaginationParams, MessageResponse
from app.modules.analytics_center.service import (
    get_analytics_overview,
    get_trend_data,
    get_multi_trend,
    get_top_resources,
    get_user_activity,
    get_asset_statistics,
    get_task_statistics
)
from app.modules.analytics_center.ai_agent import chat, get_chat_history, save_chat_message


router = APIRouter(
    prefix="/api/analytics-center",
    tags=["运营分析中心"]
)


@router.get("/overview", response_model=AnalyticsOverview)
def read_analytics_overview(
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics overview with counts and statistics.

    Returns overview of:
    - Total users, organizations, data assets
    - Total compute tasks, evidence records
    - Active tokens
    - Task completion rate
    - Average task duration
    - Recent activity (last 7 days)
    """
    return get_analytics_overview(db)


@router.get("/trend", response_model=TrendResponse)
def read_trend_data(
    metric_name: str = Query(..., description="Metric name to query"),
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    granularity: str = Query("day", description="Granularity: day, week, month"),
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend data for a specific metric.

    - **metric_name**: Name of the metric to query
    - **start_date**: Start date for the trend
    - **end_date**: End date for the trend
    - **granularity**: Aggregation granularity (day, week, month)

    Returns trend data points for the specified metric.
    """
    if granularity not in ["day", "week", "month"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="granularity must be one of: day, week, month"
        )

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )

    return get_trend_data(db, metric_name, start_date, end_date, granularity)


@router.post("/trend/multi", response_model=List[StatSeries])
def read_multi_trend(
    metric_names: List[str],
    start_date: datetime,
    end_date: datetime,
    granularity: str = "day",
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend data for multiple metrics at once.

    Request body:
    - **metric_names**: List of metric names to query
    - **start_date**: Start date for the trend
    - **end_date**: End date for the trend
    - **granularity**: Aggregation granularity (day, week, month)

    Returns list of StatSeries, one per metric.
    """
    if granularity not in ["day", "week", "month"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="granularity must be one of: day, week, month"
        )

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )

    return get_multi_trend(db, metric_names, start_date, end_date, granularity)


@router.get("/top-resources", response_model=List[Dict[str, Any]])
def read_top_resources(
    resource_type: str = Query(..., description="Resource type (e.g., data_asset, compute_task)"),
    limit: int = Query(10, ge=1, le=100, description="Number of top resources"),
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top N resources by usage count.

    - **resource_type**: Type of resource (e.g., 'data_asset', 'compute_task')
    - **limit**: Number of top resources to return (1-100)

    Returns list of top resources with usage statistics.
    """
    return get_top_resources(db, resource_type, limit)


@router.get("/user-activity", response_model=List[Dict[str, Any]])
def read_user_activity(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=100, description="Number of top users"),
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get most active users by audit log count.

    - **days**: Number of days to look back (1-365)
    - **limit**: Number of top users to return (1-100)

    Returns list of most active users with activity counts.
    """
    return get_user_activity(db, days, limit)


@router.get("/asset-stats", response_model=Dict[str, Any])
def read_asset_statistics(
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get asset statistics breakdown.

    Returns statistics by:
    - Asset type
    - Category
    - Status
    - Total size
    """
    return get_asset_statistics(db)


@router.get("/task-stats", response_model=Dict[str, Any])
def read_task_statistics(
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get task statistics breakdown.

    Returns statistics by:
    - Task type
    - Status
    - Average duration by type
    - Success rate by type
    """
    return get_task_statistics(db)


@router.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(
    request: AIChatRequest,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
):
    """
    AI chat endpoint for energy domain Q&A.

    Request body:
    - **message**: User's question
    - **session_id**: Optional session ID for conversation tracking
    - **context**: Optional context information

    Returns AI response with:
    - **message**: Assistant's reply
    - **session_id**: Session identifier
    - **sources**: List of information sources
    - **confidence**: Confidence score (0-1)

    **Supported topics:**
    - 新能源发电预测 (New energy power prediction)
    - 电力市场交易 (Electricity market trading)
    - 虚拟电厂调度 (Virtual power plant dispatch)
    - 数据安全合规 (Data security compliance)
    - 系统功能介绍 (System functionality overview)
    - 数据共享流程 (Data sharing workflow)
    - 隐私计算技术 (Privacy computing technologies)
    """
    # Get response from AI agent
    response = chat(
        message=request.message,
        session_id=request.session_id,
        context={
            "user_id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
            "organization_id": current_user.organization_id
        }
    )

    # Save messages to history (simulated)
    if request.session_id:
        # Save user message
        from datetime import datetime
        save_chat_message(request.session_id, AIChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        ))

        # Save assistant message
        save_chat_message(request.session_id, response.message)

    return response


@router.get("/ai/history", response_model=List[AIChatMessage])
def read_chat_history(
    session_id: str = Query(..., description="Session ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of messages to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get chat history for a session.

    - **session_id**: Session identifier
    - **limit**: Number of messages to return (1-50)

    Returns last N messages from the session (simulated).
    """
    history = get_chat_history(session_id, limit)

    # If no history exists, return simulated history
    if not history:
        # Generate simulated history for demo purposes
        from datetime import datetime, timedelta
        simulated_history = [
            AIChatMessage(
                role="assistant",
                content="您好！我是能源可信数据空间的AI助手。请问有什么可以帮您？",
                timestamp=datetime.utcnow() - timedelta(minutes=10)
            )
        ]
        return simulated_history

    return history
