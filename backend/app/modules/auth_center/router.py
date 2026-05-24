"""Auth Center API Router.

Provides endpoints for DID management, access policies, and token authorization.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models import AccessPolicy, AuthToken, User
from app.modules.auth_center import service as auth_service
from app.schemas import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.auth import (
    DIDCreate,
    DIDResponse,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
    TokenApply,
    TokenResponse,
    TokenReview,
    TokenVerify,
)
from app.utils.deps import get_current_user, require_role

router = APIRouter(prefix="/api/auth-center", tags=["数据授权中心"])


# ============ DID Endpoints ============
@router.post("/did/register", response_model=DIDResponse)
def register_did(
    did_in: DIDCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Register a new DID document.

    Creates a new decentralized identifier for the current user.
    """
    did_doc = auth_service.register_did(db, current_user.id, did_in)
    return DIDResponse.model_validate(did_doc)


@router.get("/did/list", response_model=PaginatedResponse[DIDResponse])
def list_dids(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """List DID documents accessible to the current user.

    Users can only see their own DID documents unless they are admin/operator.
    """
    from app.models import DIDDocument

    query = db.query(DIDDocument)

    # Regular users only see their own DIDs
    if current_user.role not in ["admin", "operator"]:
        query = query.filter(DIDDocument.created_by == current_user.id)

    total = query.count()
    items = query.order_by(DIDDocument.id.desc()).offset(
        (pagination.page - 1) * pagination.page_size
    ).limit(pagination.page_size).all()

    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=[DIDResponse.model_validate(item) for item in items],
    )


@router.get("/did/{did}", response_model=DIDResponse)
def get_did(
    did: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Resolve a DID to its document."""
    did_doc = auth_service.resolve_did(db, did)
    if not did_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DID not found"
        )
    return DIDResponse.model_validate(did_doc)


@router.post("/did/verify-signature")
def verify_did_signature(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Verify a signature made with a DID's private key.

    Request body:
        - did: The DID that signed the data
        - data: The original data
        - signature: The signature to verify
    """
    did = payload.get("did")
    data = payload.get("data")
    signature = payload.get("signature")

    if not all([did, data, signature]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: did, data, signature"
        )

    result = auth_service.verify_did_signature(db, did, data, signature)
    return {"valid": result["valid"], "reason": result.get("reason")}


# ============ Policy Endpoints ============
@router.post("/policy", response_model=PolicyResponse)
def create_policy(
    policy_in: PolicyCreate,
    current_user: User = Depends(require_role("admin", "operator")),
    db: Session = Depends(get_sync_db),
):
    """Create a new access policy.

    Requires admin or operator role.
    """
    policy = auth_service.create_policy(db, current_user.id, policy_in)
    return PolicyResponse.model_validate(policy)


@router.get("/policy/list", response_model=PaginatedResponse[PolicyResponse])
def list_policies(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """List all active access policies."""
    items, total = auth_service.BaseService(AccessPolicy).get_list(
        db, pagination, filters={"status": "active"}
    )

    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=[PolicyResponse.model_validate(item) for item in items],
    )


@router.get("/policy/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Get a specific access policy by ID."""
    from app.modules.module_base import BaseService

    policy = BaseService(AccessPolicy).get_or_404(db, policy_id)
    return PolicyResponse.model_validate(policy)


@router.put("/policy/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    policy_in: PolicyUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_sync_db),
):
    """Update an access policy.

    Requires admin role.
    """
    from app.modules.module_base import BaseService

    db_policy = BaseService(AccessPolicy).get_or_404(db, policy_id)
    updated = BaseService(AccessPolicy).update(db, db_policy, policy_in)
    return PolicyResponse.model_validate(updated)


@router.delete("/policy/{policy_id}", response_model=MessageResponse)
def delete_policy(
    policy_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_sync_db),
):
    """Delete (deactivate) an access policy.

    Requires admin role. This performs a soft delete by setting status to 'deleted'.
    """
    from app.modules.module_base import BaseService

    db_policy = BaseService(AccessPolicy).get_or_404(db, policy_id)
    db_policy.status = "deleted"
    db.commit()

    return MessageResponse(message="Policy deleted successfully")


# ============ Token Endpoints ============
@router.post("/token/apply", response_model=TokenResponse)
def apply_token(
    token_in: TokenApply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Apply for a new authentication token.

    Creates a token application that requires admin approval.
    """
    token = auth_service.apply_token(db, current_user.id, token_in)
    return TokenResponse.model_validate(token)


@router.get("/token/list", response_model=PaginatedResponse[TokenResponse])
def list_tokens(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """List authentication tokens.

    Regular users see only their own tokens. Admins see all tokens.
    """
    query = db.query(AuthToken)

    # Regular users only see their own tokens
    if current_user.role not in ["admin", "operator"]:
        query = query.filter(AuthToken.applicant_id == current_user.id)

    total = query.count()
    items = query.order_by(AuthToken.id.desc()).offset(
        (pagination.page - 1) * pagination.page_size
    ).limit(pagination.page_size).all()

    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=[TokenResponse.model_validate(item) for item in items],
    )


@router.get("/token/{token_id}", response_model=TokenResponse)
def get_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Get a specific token by ID."""
    token = db.query(AuthToken).filter(AuthToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Check access
    if current_user.role not in ["admin", "operator"] and token.applicant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this token"
        )

    return TokenResponse.model_validate(token)


@router.post("/token/{token_id}/review", response_model=TokenResponse)
def review_token(
    token_id: int,
    review_in: TokenReview,
    current_user: User = Depends(require_role("admin", "operator")),
    db: Session = Depends(get_sync_db),
):
    """Review (approve/reject) a token application.

    Requires admin or operator role.
    """
    token = auth_service.review_token(db, current_user.id, token_id, review_in)
    return TokenResponse.model_validate(token)


@router.post("/token/{token_id}/revoke", response_model=TokenResponse)
def revoke_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Revoke an authentication token.

    Users can revoke their own tokens. Admins can revoke any token.
    """
    token = auth_service.revoke_token(db, current_user.id, token_id)
    return TokenResponse.model_validate(token)


@router.post("/token/verify")
def verify_token(
    verify_in: TokenVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Verify a token's validity for accessing a resource.

    Returns detailed validity information including expiration and policy details.
    """
    result = auth_service.verify_token(db, verify_in)
    return result


# Alias for BaseService import
from app.modules.module_base import BaseService
