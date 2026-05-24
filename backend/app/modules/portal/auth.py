"""Portal authentication module."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, Organization
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import TokenResponse as SchemaTokenResponse
from app.core.security import hash_password, verify_password, create_access_token


def register_user(db: Session, user_in: UserCreate) -> User:
    """
    Register a new user.
    Creates user and organization if needed.
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # Check if email already exists (if provided)
    if user_in.email:
        existing_email = db.query(User).filter(User.email == user_in.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册",
            )

    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == user_in.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织不存在",
        )

    if org.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织已被禁用",
        )

    # Create new user
    hashed_password = hash_password(user_in.password)
    new_user = User(
        username=user_in.username,
        password_hash=hashed_password,
        real_name=user_in.real_name,
        email=user_in.email,
        phone=user_in.phone,
        org_id=user_in.org_id,
        role=user_in.role,
        status="active",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate user with username and password.
    Returns User if successful, None otherwise.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    if user.status != "active":
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_user_token(user: User) -> SchemaTokenResponse:
    """
    Create JWT access token for user.
    Returns TokenResponse with access token and user info.
    """
    access_token = create_access_token(
        subject=str(user.id),
        username=user.username,
        role=user.role,
    )

    user_response = UserResponse.model_validate(user)

    return SchemaTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response,
    )
