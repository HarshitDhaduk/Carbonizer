"""Auth endpoints.

With USE_DB=true: register persists a User (+ PrivacySettings) with an Argon2 hash,
login verifies the hash from Postgres, and the JWT subject is the user's UUID.
With USE_DB=false: a single demo user (from settings) can log in; register is
unavailable (503).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import PrivacySettings, User
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])

# subject used for the demo user in seed mode (no DB)
DEMO_USER_ID = "usr_demo"


def _token(subject: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject),
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession | None = Depends(get_db),
) -> TokenResponse:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration requires the database (set USE_DB=true).",
        )
    email = body.email.strip().lower()
    existing = await db.execute(select(User.id).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        region=body.region,
    )
    user.privacy = PrivacySettings()
    db.add(user)
    await db.flush()
    await audit.record(
        db,
        action="auth.register",
        actor=str(user.id),
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )
    await db.commit()
    await db.refresh(user)
    return _token(str(user.id))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession | None = Depends(get_db),
) -> TokenResponse:
    email = form.username.strip().lower()

    # seed mode — validate against demo credentials
    if db is None:
        if email != settings.demo_email or form.password != settings.demo_password:
            raise _bad_credentials()
        return _token(DEMO_USER_ID)

    # DB mode — verify the Argon2 hash
    res = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = res.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password_hash):
        await audit.record(
            db,
            action="auth.login.failed",
            actor=str(user.id) if user else None,
            resource_type="user",
            resource_id=str(user.id) if user else None,
            request=request,
        )
        await db.commit()
        raise _bad_credentials()
    await audit.record(
        db,
        action="auth.login.success",
        actor=str(user.id),
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )
    await db.commit()
    return _token(str(user.id))


@router.get("/me", response_model=UserOut)
async def me(
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> UserOut:
    # seed-mode / demo subject
    if db is None or subject == DEMO_USER_ID:
        return UserOut(
            id=subject, email=settings.demo_email, region="GB", target_tco2e=3.5
        )
    try:
        uid = uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc
    res = await db.execute(select(User).where(User.id == uid))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserOut(
        id=str(user.id),
        email=user.email,
        region=user.region,
        target_tco2e=float(user.target_tco2e) if user.target_tco2e is not None else None,
    )


def _bad_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )
