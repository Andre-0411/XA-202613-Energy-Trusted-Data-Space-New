from datetime import datetime, date
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class StatPoint(BaseModel):
    date: str
    value: Any


class StatSeries(BaseModel):
    metric_name: str
    unit: str = ""
    data: List[StatPoint] = []


class AnalyticsOverview(BaseModel):
    total_users: int
    total_organizations: int
    total_assets: int
    total_compute_tasks: int
    total_evidence_records: int
    total_auth_tokens: int
    task_completion_rate: float
    avg_task_duration: Optional[float] = None


class TrendRequest(BaseModel):
    metric_name: str = Field(..., description="统计指标名称")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    granularity: str = Field(default="day", description="day/week/month")


class TrendResponse(BaseModel):
    metric_name: str
    granularity: str
    data: List[StatPoint] = []


class AIChatMessage(BaseModel):
    role: str = Field(..., description="user/assistant")
    content: str


class AIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AIChatResponse(BaseModel):
    reply: str
    session_id: str
    sources: List[Dict[str, Any]] = []
    confidence: float = 0.0
