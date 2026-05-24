from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    asset_type: str = Field(..., description="dataset/model/api/service")
    category: Optional[str] = Field(None, description="generation/consumption/trading/market")
    did: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    data_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    record_count: Optional[int] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    asset_type: str
    category: Optional[str]
    owner_id: int
    did: Optional[str]
    metadata: Optional[Dict[str, Any]]
    data_hash: Optional[str]
    size_bytes: Optional[int]
    record_count: Optional[int]
    status: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetWithOwner(AssetResponse):
    owner_name: Optional[str] = None
