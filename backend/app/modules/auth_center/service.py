"""Auth Center Business Logic Service."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import AccessPolicy, AuthToken, DIDDocument
from app.modules.auth_center.crypto import generate_sm2_keypair, sm2_sign, sm2_verify
from app.schemas.auth import (
    DIDCreate,
    PolicyCreate,
    TokenApply,
    TokenReview,
    TokenVerify,
)


def register_did(db: Session, user_id: int, did_in: DIDCreate) -> DIDDocument:
    """Register a new DID document.

    Args:
        db: Database session.
        user_id: ID of the user creating the DID.
        did_in: DID creation data.

    Returns:
        The created DIDDocument.
    """
    # Generate keypair if not provided
    if not did_in.public_key:
        private_key, public_key = generate_sm2_keypair()
    else:
        public_key = did_in.public_key
        private_key = None  # Private key is not stored

    # Generate DID with format: did:energy:user-{id}-{random_hex}
    random_hex = secrets.token_hex(8)
    did = f"did:energy:user-{user_id}-{random_hex}"

    # Use provided controller or default to the DID itself
    controller = did_in.controller or did

    db_did = DIDDocument(
        did=did,
        controller=controller,
        public_key=public_key,
        public_key_type=did_in.public_key_type or "SM2",
        verification_method=did_in.verification_method,
        service_endpoint=did_in.service_endpoint,
        created_by=user_id,
        status="active",
    )

    db.add(db_did)
    db.commit()
    db.refresh(db_did)
    return db_did


def resolve_did(db: Session, did: str) -> Optional[DIDDocument]:
    """Resolve a DID to its document.

    Args:
        db: Database session.
        did: The DID to resolve.

    Returns:
        The DIDDocument if found, None otherwise.
    """
    return db.query(DIDDocument).filter(
        DIDDocument.did == did,
        DIDDocument.status == "active"
    ).first()


def verify_did_signature(db: Session, did: str, data: str, signature: str) -> Dict[str, Any]:
    """Verify a signature made with a DID's private key.

    Args:
        db: Database session.
        did: The DID that signed the data.
        data: The original data.
        signature: The signature to verify.

    Returns:
        Dict with 'valid' boolean and optional 'did_document'.
    """
    did_doc = resolve_did(db, did)
    if not did_doc:
        return {"valid": False, "reason": "DID not found or inactive"}

    is_valid = sm2_verify(data, signature, did_doc.public_key)
    return {
        "valid": is_valid,
        "reason": None if is_valid else "Signature verification failed",
        "did_document": did_doc if is_valid else None,
    }


def create_policy(db: Session, user_id: int, policy_in: PolicyCreate) -> AccessPolicy:
    """Create a new access policy.

    Args:
        db: Database session.
        user_id: ID of the user creating the policy.
        policy_in: Policy creation data.

    Returns:
        The created AccessPolicy.
    """
    db_policy = AccessPolicy(
        name=policy_in.name,
        description=policy_in.description,
        resource_type=policy_in.resource_type,
        conditions=policy_in.conditions,
        effect=policy_in.effect or "allow",
        priority=policy_in.priority or 0,
        created_by=user_id,
        status="active",
    )

    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


def evaluate_policy(policy: AccessPolicy, context: Dict[str, Any]) -> bool:
    """Evaluate an ABAC policy against a request context.

    Args:
        policy: The policy to evaluate.
        context: Request context containing attributes like:
            - user_role: Role of the requesting user
            - user_org: Organization of the user
            - resource_type: Type of resource being accessed
            - time_range: Optional time constraints

    Returns:
        True if access should be granted, False otherwise.
    """
    conditions = policy.conditions

    # Check resource type condition
    if "resource_type" in conditions:
        if context.get("resource_type") != conditions["resource_type"]:
            return policy.effect == "deny"

    # Check user role condition
    if "roles" in conditions:
        if context.get("user_role") not in conditions["roles"]:
            return policy.effect == "deny"

    # Check organization condition
    if "organizations" in conditions:
        if context.get("user_org") not in conditions["organizations"]:
            return policy.effect == "deny"

    # Check time range condition
    if "time_start" in conditions:
        current_time = datetime.now(timezone.utc)
        start_time = datetime.fromisoformat(conditions["time_start"])
        if current_time < start_time:
            return policy.effect == "deny"

    if "time_end" in conditions:
        current_time = datetime.now(timezone.utc)
        end_time = datetime.fromisoformat(conditions["time_end"])
        if current_time > end_time:
            return policy.effect == "deny"

    # All conditions met
    return policy.effect == "allow"


def apply_token(db: Session, user_id: int, token_in: TokenApply) -> AuthToken:
    """Apply for a new authentication token.

    Args:
        db: Database session.
        user_id: ID of the applicant.
        token_in: Token application data.

    Returns:
        The created AuthToken in 'pending' status.
    """
    # Generate unique token code
    token_code = f"ATK-{secrets.token_urlsafe(24)}"

    # Calculate expiration time
    expires_at = datetime.now(timezone.utc) + timedelta(hours=token_in.expires_hours)

    db_token = AuthToken(
        token_code=token_code,
        applicant_id=user_id,
        policy_id=token_in.policy_id,
        purpose=token_in.purpose,
        status="pending",
        expires_at=expires_at,
    )

    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def review_token(db: Session, reviewer_id: int, token_id: int, review_in: TokenReview) -> AuthToken:
    """Review (approve/reject) a token application.

    Args:
        db: Database session.
        reviewer_id: ID of the user reviewing the token.
        token_id: ID of the token to review.
        review_in: Review decision data.

    Returns:
        The updated AuthToken.

    Raises:
        HTTPException: If token not found or not in pending status.
    """
    from fastapi import HTTPException, status

    token = db.query(AuthToken).filter(AuthToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    if token.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token cannot be reviewed: current status is '{token.status}'"
        )

    token.status = "approved" if review_in.approved else "rejected"
    token.approved_by = reviewer_id
    token.approved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(token)
    return token


def revoke_token(db: Session, user_id: int, token_id: int) -> AuthToken:
    """Revoke an existing token.

    Args:
        db: Database session.
        user_id: ID of the user requesting revocation (must be owner or admin).
        token_id: ID of the token to revoke.

    Returns:
        The updated AuthToken.

    Raises:
        HTTPException: If token not found or user not authorized.
    """
    from fastapi import HTTPException, status

    token = db.query(AuthToken).filter(AuthToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Check if user owns the token or is an admin
    # Note: In production, you'd also check for admin role
    if token.applicant_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this token"
        )

    token.status = "revoked"
    db.commit()
    db.refresh(token)
    return token


def verify_token(db: Session, verify_in: TokenVerify) -> Dict[str, Any]:
    """Verify a token's validity.

    Args:
        db: Database session.
        verify_in: Token verification data.

    Returns:
        Dict with validity status and additional details.
    """
    token = db.query(AuthToken).filter(
        AuthToken.token_code == verify_in.token_code
    ).first()

    if not token:
        return {
            "valid": False,
            "reason": "Token not found",
            "token_id": None,
            "status": None,
        }

    # Check status
    if token.status != "approved":
        return {
            "valid": False,
            "reason": f"Token status is '{token.status}'",
            "token_id": token.id,
            "status": token.status,
        }

    # Check expiration
    now = datetime.now(timezone.utc)
    if token.expires_at < now:
        return {
            "valid": False,
            "reason": "Token has expired",
            "token_id": token.id,
            "status": token.status,
            "expired_at": token.expires_at.isoformat(),
        }

    # Get associated policy for resource type check
    from app.models import AccessPolicy
    policy = db.query(AccessPolicy).filter(
        AccessPolicy.id == token.policy_id
    ).first()

    if not policy:
        return {
            "valid": False,
            "reason": "Associated policy not found",
            "token_id": token.id,
            "status": token.status,
        }

    # Check resource type match
    if verify_in.resource_type and policy.resource_type != verify_in.resource_type:
        return {
            "valid": False,
            "reason": f"Resource type mismatch: token allows '{policy.resource_type}', requested '{verify_in.resource_type}'",
            "token_id": token.id,
            "status": token.status,
        }

    return {
        "valid": True,
        "reason": None,
        "token_id": token.id,
        "status": token.status,
        "policy_id": token.policy_id,
        "policy_name": policy.name,
        "resource_type": policy.resource_type,
        "applicant_id": token.applicant_id,
        "expires_at": token.expires_at.isoformat(),
    }
