"""Portal router module."""

from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.utils.deps import get_current_user
from app.models import User, Organization
from app.schemas.user import UserCreate, UserResponse, UserWithOrg
from app.schemas import DashboardOverview
from app.modules.portal.auth import register_user, authenticate_user, create_user_token
from app.modules.portal.service import get_dashboard_overview, get_system_announcements

router = APIRouter(prefix="/api/portal", tags=["门户"])


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_sync_db)):
    """
    Register a new user.
    Creates user and returns user info.
    """
    user = register_user(db, user_in)
    return UserResponse.model_validate(user)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_sync_db),
):
    """
    User login with OAuth2 password flow.
    Returns access token and user info.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_user_token(user)


@router.get("/me", response_model=UserWithOrg)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """
    Get current user info with organization details.
    """
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()

    user_dict = UserResponse.model_validate(current_user).model_dump()
    user_dict["org_name"] = org.name if org else None
    user_dict["org_type"] = org.type if org else None

    return UserWithOrg(**user_dict)


@router.get("/dashboard", response_model=DashboardOverview)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """
    Get portal dashboard overview.
    Returns aggregated stats, recent activities, system status, and announcements.
    """
    overview = get_dashboard_overview(db)
    return overview


@router.get("/announcements", response_model=List[Dict[str, Any]])
def get_announcements(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """
    Get system announcements.
    Returns list of announcement dicts.
    """
    announcements = get_system_announcements(db, limit=limit)
    return announcements


@router.get("/health")
def health_check():
    """
    Health check endpoint (no auth required).
    Returns system status info.
    """
    from app.config import get_settings
    settings = get_settings()

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }
