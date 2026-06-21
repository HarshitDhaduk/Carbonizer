"""Auth endpoints.

With USE_DB=true: register persists a User (+ PrivacySettings) with an Argon2 hash,
login verifies the hash from Postgres, and the JWT subject is the user's UUID.
With USE_DB=false: a single demo user (from settings) can log in; register is
unavailable (503).

Phase 2.1 (Improvement Plan): Tokens are issued as ``HttpOnly`` cookies, not as
JSON. The legacy ``TokenResponse`` body is kept (with the access token blanked)
so any non-browser client still gets a 2xx with a sane shape; browser clients
read the cookie automatically.
"""

from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.config import settings
from app.core.cookies import (
    clear_auth_cookies,
    generate_csrf_token,
    set_auth_cookies,
)
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    decode_token,
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


_SECONDS_PER_MINUTE = 60
_SECONDS_PER_DAY = 24 * 60 * _SECONDS_PER_MINUTE


def _token_response(subject: str) -> TokenResponse:
    """Body returned alongside the cookie set.

    The browser uses the HttpOnly cookie. The body keeps an access token for
    machine clients (Swagger UI, tests, future CLI). The frontend SPA must
    ignore the body field — see ``frontend/src/lib/client-api.ts``.
    """
    return TokenResponse(
        access_token=create_access_token(subject),
        expires_in=settings.access_token_ttl_minutes * _SECONDS_PER_MINUTE,
    )


async def _audit_and_commit(
    db: AsyncSession,
    request: Request,
    action: str,
    actor: str | None,
) -> None:
    """Record an audit-log row keyed on the user, then commit the transaction."""
    await audit.record(
        db,
        action=action,
        actor=actor,
        resource_type="user",
        resource_id=actor,
        request=request,
    )
    await db.commit()


def _issue_session(response: Response, subject: str) -> TokenResponse:
    """Set the auth-cookie trio and return the back-compat token body."""
    set_auth_cookies(response, subject)
    return _token_response(subject)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description=(
        "Creates a User + PrivacySettings row, hashes the password with "
        "Argon2id, and sets the `cb_access` / `cb_refresh` / `cb_csrf` "
        "session cookies (see ADR-0003). Returns the access JWT in the "
        "body as a back-compat for machine clients; the SPA ignores it "
        "and relies on the cookie. Rate-limited to 3/hour per IP."
    ),
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: AsyncSession | None = Depends(get_db),
) -> TokenResponse:
    """Create a new user account + session cookies in one round-trip."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration requires the database (set USE_DB=true).",
        )
    email = body.email.strip().lower()
    if await _email_exists(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
    user = await _create_user(db, email, body.password, body.region)
    await _audit_and_commit(db, request, "auth.register", str(user.id))
    await db.refresh(user)
    return _issue_session(response, str(user.id))


async def _email_exists(db: AsyncSession, email: str) -> bool:
    """True when a non-deleted user already owns ``email``."""
    res = await db.execute(select(User.id).where(User.email == email))
    return res.scalar_one_or_none() is not None


async def _create_user(
    db: AsyncSession, email: str, password: str, region: str
) -> User:
    """Insert the user + their default PrivacySettings row."""
    user = User(
        email=email, password_hash=hash_password(password), region=region
    )
    user.privacy = PrivacySettings()
    db.add(user)
    await db.flush()
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in (OAuth2 password grant)",
    description=(
        "Verifies an Argon2id password hash and sets the session cookie "
        "trio. Rate-limited to 5/minute per IP; on credential-stuffing "
        "patterns the email-scoped limiter kicks in too. Failed attempts "
        "are written to the audit log."
    ),
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession | None = Depends(get_db),
) -> TokenResponse:
    """Verify password (Argon2id), issue session cookies, return access JWT."""
    email = form.username.strip().lower()
    if db is None:
        return _login_seed_mode(response, email, form.password)
    return await _login_db_mode(db, request, response, email, form.password)


def _login_seed_mode(response: Response, email: str, password: str) -> TokenResponse:
    """Seed-mode auth — only the demo credentials work."""
    if email != settings.demo_email or password != settings.demo_password:
        raise _bad_credentials()
    return _issue_session(response, DEMO_USER_ID)


async def _login_db_mode(
    db: AsyncSession,
    request: Request,
    response: Response,
    email: str,
    password: str,
) -> TokenResponse:
    """DB-mode auth — verify the Argon2 hash, audit both branches."""
    res = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = res.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        actor = str(user.id) if user else None
        await _audit_and_commit(db, request, "auth.login.failed", actor)
        raise _bad_credentials()
    await _audit_and_commit(db, request, "auth.login.success", str(user.id))
    return _issue_session(response, str(user.id))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate the access + CSRF cookies",
)
async def refresh(request: Request, response: Response) -> TokenResponse:
    """Rotate the access + CSRF cookies using the refresh JWT.

    The refresh cookie is HttpOnly and ``Path=/api/v1/auth`` so the browser
    only sends it on this endpoint. Successful refresh issues a fresh CSRF
    token too — long-running tabs stay in sync after the previous one ages
    out alongside the access cookie.
    """
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise _unauthenticated()
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise _unauthenticated() from exc
    if payload.get("type") != "refresh":
        raise _unauthenticated()
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _unauthenticated()
    set_auth_cookies(response, subject)
    return _token_response(subject)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the session cookies",
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession | None = Depends(get_db),
) -> Response:
    """Clear all three auth cookies. Idempotent — safe to call when already signed out."""
    # Best-effort audit; works even if the caller's access cookie has expired.
    subject = None
    access_token = request.cookies.get(settings.access_cookie_name)
    if access_token:
        try:
            payload = decode_token(access_token)
            subject = payload.get("sub") if payload.get("type") == "access" else None
        except jwt.PyJWTError:
            subject = None
    if db is not None and subject is not None:
        await audit.record(
            db,
            action="auth.logout",
            actor=subject,
            resource_type="user",
            resource_id=subject,
            request=request,
        )
        await db.commit()
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/csrf",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Lazily issue a CSRF cookie",
)
async def issue_csrf(request: Request, response: Response) -> Response:
    """Set a fresh ``cb_csrf`` cookie if the caller doesn't already have one.

    The frontend calls this once on boot before its first state-changing
    request, so the CSRF middleware has something to compare against. Idempotent
    when a cookie already exists — we re-issue rather than refuse so a stale
    value from a logged-out session can't wedge the client.
    """
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=generate_csrf_token(),
        max_age=settings.refresh_token_ttl_days * _SECONDS_PER_DAY,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/me",
    response_model=UserOut,
    summary="Profile of the currently-signed-in user",
)
async def me(
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> UserOut:
    """Return the currently authenticated user's public profile."""
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


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
