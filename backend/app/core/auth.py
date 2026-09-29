import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.models import Account, Session
from app.core.security import (
    SESSION_SECONDS,
    read_cookie,
    read_state,
    sign_state,
    signer,
    token_digest,
)

Db = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(prefix="/api/auth", tags=["auth"])
OAUTH_STATE_COOKIE = "qa_report_oauth_state"


class AuthState(BaseModel):
    authenticated: bool = False
    account_id: UUID | None = None
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    google_ready: bool = False


def frontend_origin() -> str:
    return get_settings().allowed_origins.split(",")[0].strip().rstrip("/")


async def session_account(request: Request, db: AsyncSession) -> Account | None:
    digest = read_cookie(request.cookies.get(get_settings().session_cookie_name))
    if digest is None:
        return None
    return await db.scalar(
        select(Account)
        .join(Session)
        .where(
            Session.token_hash == digest,
            Session.expires_at > datetime.now(UTC),
        )
    )


async def require_user(request: Request, db: Db) -> Account:
    account = await session_account(request, db)
    if account is None:
        raise AppError(401, "Sesi berakhir. Masuk kembali untuk melanjutkan.")
    return account


User = Annotated[Account, Depends(require_user)]


async def account_db(db: Db, user: User) -> AsyncSession:
    db.info["account_id"] = user.id
    return db


OwnedDb = Annotated[AsyncSession, Depends(account_db)]


def auth_state(account: Account | None) -> AuthState:
    if account is None:
        return AuthState(
            google_ready=bool(
                get_settings().google_client_id
                and get_settings().google_client_secret.get_secret_value()
            )
        )
    return AuthState(
        authenticated=True,
        account_id=account.id,
        email=account.email,
        display_name=account.display_name,
        avatar_url=account.avatar_url,
        google_ready=True,
    )


async def issue_session(
    db: AsyncSession, response: Response, request: Request, account: Account
) -> None:
    now = datetime.now(UTC)
    previous = read_cookie(request.cookies.get(get_settings().session_cookie_name))
    await db.execute(
        delete(Session).where((Session.expires_at <= now) | (Session.token_hash == previous))
    )
    token = secrets.token_urlsafe(32)
    db.add(
        Session(
            token_hash=token_digest(token),
            account_id=account.id,
            expires_at=now + timedelta(seconds=SESSION_SECONDS),
        )
    )
    await db.commit()
    response.set_cookie(
        get_settings().session_cookie_name,
        signer().dumps(token),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="none" if get_settings().cookie_secure else "lax",
        path="/",
    )


@router.get("/status")
async def status(request: Request, db: Db) -> AuthState:
    return auth_state(await session_account(request, db))


@router.get("/me")
async def me(user: User) -> AuthState:
    return auth_state(user)


@router.get("/google/start")
async def google_start(response: Response) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError(503, "Google Login belum dikonfigurasi di backend.")
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    redirect = RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302
    )
    redirect.set_cookie(
        OAUTH_STATE_COOKIE,
        sign_state(state),
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth/google",
    )
    return redirect


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Db,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if (
        error
        or not code
        or not state
        or not secrets.compare_digest(
            state, read_state(request.cookies.get(OAUTH_STATE_COOKIE)) or ""
        )
    ):
        raise AppError(400, "Login Google dibatalkan atau tidak valid.")
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret.get_secret_value(),
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_redirect_uri,
                },
            )
            if token_response.status_code != 200:
                raise AppError(502, "Google tidak menerima proses login.")
            access_token = token_response.json().get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise AppError(502, "Google tidak mengembalikan token login.")
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if profile_response.status_code != 200:
                raise AppError(502, "Profil Google tidak dapat diverifikasi.")
            profile = profile_response.json()
    except AppError:
        raise
    except httpx.HTTPError:
        raise AppError(502, "Google tidak dapat dihubungi. Coba lagi.") from None

    google_sub = profile.get("sub")
    email = profile.get("email")
    email_verified = profile.get("email_verified") is True
    if not isinstance(google_sub, str) or not isinstance(email, str) or not email_verified:
        raise AppError(403, "Akun Google belum memiliki email terverifikasi.")
    email = email.lower()
    if settings.allowed_email_set and email not in settings.allowed_email_set:
        raise AppError(403, "Akun Google ini belum diizinkan menggunakan QA Report.")

    account = await db.scalar(
        select(Account).where(Account.google_sub == google_sub).with_for_update()
    )
    if account is None:
        account = Account(
            google_sub=google_sub,
            email=email,
            display_name=str(profile.get("name") or email),
            avatar_url=profile.get("picture") if isinstance(profile.get("picture"), str) else None,
        )
        db.add(account)
        await db.flush()
    else:
        account.email = email
        account.display_name = str(profile.get("name") or email)
        account.avatar_url = (
            profile.get("picture") if isinstance(profile.get("picture"), str) else None
        )
        account.last_login_at = datetime.now(UTC)
    response = RedirectResponse(frontend_origin(), status_code=302)
    await issue_session(db, response, request, account)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/api/auth/google")
    return response


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: Db) -> None:
    digest = read_cookie(request.cookies.get(get_settings().session_cookie_name))
    if digest:
        await db.execute(delete(Session).where(Session.token_hash == digest))
        await db.commit()
    response.delete_cookie(
        get_settings().session_cookie_name,
        path="/",
        httponly=True,
        samesite="none" if get_settings().cookie_secure else "lax",
        secure=get_settings().cookie_secure,
    )
