import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import User, require_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.models import YouTubeConnection
from app.core.security import decrypt_secret, encrypt_secret, read_state, sign_state

router = APIRouter(prefix="/api/youtube", tags=["youtube"], dependencies=[Depends(require_user)])
Db = Annotated[AsyncSession, Depends(get_db)]
STATE_COOKIE = "qa_report_youtube_state"
UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
READ_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
CHUNK_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 512 * 1024 * 1024


class YouTubeStatus(BaseModel):
    connected: bool
    channel_title: str | None = None
    connected_by: str | None = None
    connected_at: datetime | None = None
    can_connect: bool


class VideoItem(BaseModel):
    video_id: str
    title: str
    description: str
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    privacy_status: str


class VideoPage(BaseModel):
    videos: list[VideoItem]
    next_page_token: str | None = None


class UploadResult(BaseModel):
    video_id: str
    url: str


def is_admin(user: User) -> bool:
    admin_email = get_settings().youtube_admin_email.strip().lower()
    return bool(admin_email and user.email.lower() == admin_email)


async def connection(db: AsyncSession) -> YouTubeConnection:
    result = await db.scalar(select(YouTubeConnection).where(YouTubeConnection.id == 1))
    if result is None:
        raise AppError(503, "Akun YouTube bersama belum dihubungkan oleh admin.")
    return result


async def access_token(db: AsyncSession) -> tuple[str, YouTubeConnection]:
    linked = await connection(db)
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret.get_secret_value(),
                    "refresh_token": decrypt_secret(linked.refresh_token_encrypted),
                    "grant_type": "refresh_token",
                },
            )
    except httpx.HTTPError:
        raise AppError(502, "Google tidak dapat dihubungi. Coba lagi.") from None
    payload = response.json()
    token = payload.get("access_token")
    if response.status_code != 200 or not isinstance(token, str):
        raise AppError(401, "Koneksi YouTube kedaluwarsa. Admin perlu menghubungkan ulang.")
    return token, linked


@router.get("/status")
async def status(user: User, db: Db) -> YouTubeStatus:
    linked = await db.scalar(select(YouTubeConnection).where(YouTubeConnection.id == 1))
    return YouTubeStatus(
        connected=linked is not None,
        channel_title=linked.channel_title if linked else None,
        connected_by=linked.connected_by if linked else None,
        connected_at=linked.connected_at if linked else None,
        can_connect=is_admin(user),
    )


@router.get("/connect")
async def connect(user: User) -> RedirectResponse:
    settings = get_settings()
    if not is_admin(user):
        raise AppError(403, "Hanya admin yang dapat menghubungkan channel YouTube bersama.")
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError(503, "Google OAuth belum dikonfigurasi di backend.")
    if not settings.youtube_redirect_uri:
        raise AppError(503, "YOUTUBE_REDIRECT_URI belum dikonfigurasi di backend.")
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.youtube_redirect_uri,
            "response_type": "code",
            "scope": f"{UPLOAD_SCOPE} {READ_SCOPE}",
            "state": state,
            "access_type": "offline",
            "prompt": "consent select_account",
            "include_granted_scopes": "true",
        }
    )
    response = RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302
    )
    response.set_cookie(
        STATE_COOKIE,
        sign_state(state),
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/youtube/callback",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    user: User,
    db: Db,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    settings = get_settings()
    saved_state = read_state(request.cookies.get(STATE_COOKIE))
    if not is_admin(user):
        raise AppError(403, "Hanya admin yang dapat menghubungkan channel YouTube bersama.")
    if error or not code or not state or not secrets.compare_digest(state, saved_state or ""):
        raise AppError(400, "Koneksi YouTube dibatalkan atau tidak valid.")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret.get_secret_value(),
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.youtube_redirect_uri,
                },
            )
            token_payload = token_response.json()
            access = token_payload.get("access_token")
            refresh = token_payload.get("refresh_token")
            if token_response.status_code != 200 or not isinstance(access, str):
                raise AppError(502, "Google gagal memberikan akses YouTube.")
            if not isinstance(refresh, str):
                prior = await db.scalar(select(YouTubeConnection).where(YouTubeConnection.id == 1))
                refresh = decrypt_secret(prior.refresh_token_encrypted) if prior else None
            if not isinstance(refresh, str):
                raise AppError(502, "Google tidak memberikan refresh token. Hubungkan ulang dengan consent.")
            channel_response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet,contentDetails", "mine": "true"},
                headers={"Authorization": f"Bearer {access}"},
            )
    except AppError:
        raise
    except httpx.HTTPError:
        raise AppError(502, "Google tidak dapat dihubungi. Coba lagi.") from None
    channels = channel_response.json().get("items", [])
    if channel_response.status_code != 200 or not channels:
        raise AppError(422, "Akun Google ini belum memiliki channel YouTube.")
    channel = channels[0]
    uploads_playlist_id = (
        channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    )
    if not isinstance(uploads_playlist_id, str):
        raise AppError(422, "Playlist video channel YouTube tidak dapat ditemukan.")
    current = await db.scalar(select(YouTubeConnection).where(YouTubeConnection.id == 1))
    if current is None:
        current = YouTubeConnection(
            id=1,
            channel_id=channel["id"],
            uploads_playlist_id=uploads_playlist_id,
            channel_title=channel["snippet"]["title"],
            refresh_token_encrypted=encrypt_secret(refresh),
            connected_by=user.email,
        )
        db.add(current)
    else:
        current.channel_id = channel["id"]
        current.uploads_playlist_id = uploads_playlist_id
        current.channel_title = channel["snippet"]["title"]
        current.refresh_token_encrypted = encrypt_secret(refresh)
        current.connected_by = user.email
        current.connected_at = datetime.now(UTC)
    await db.commit()
    response = RedirectResponse(f"{settings.allowed_origins.split(',')[0].rstrip('/')}/youtube?connected=1")
    response.delete_cookie(STATE_COOKIE, path="/api/youtube/callback")
    return response


@router.delete("/connection", status_code=204)
async def disconnect(user: User, db: Db) -> None:
    if not is_admin(user):
        raise AppError(403, "Hanya admin yang dapat melepas koneksi YouTube.")
    linked = await db.scalar(select(YouTubeConnection).where(YouTubeConnection.id == 1))
    if linked:
        await db.delete(linked)
        await db.commit()


@router.get("/videos")
async def videos(
    db: Db,
    page_token: str | None = None,
) -> VideoPage:
    token, linked = await access_token(db)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params={
                    "part": "snippet,contentDetails,status",
                    "playlistId": linked.uploads_playlist_id,
                    "maxResults": 50,
                    **({"pageToken": page_token} if page_token else {}),
                },
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        raise AppError(502, "Daftar konten YouTube tidak dapat dimuat.") from None
    if response.status_code != 200:
        raise AppError(502, "YouTube menolak permintaan daftar konten.")
    payload = response.json()
    output = []
    for item in payload.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("contentDetails", {}).get("videoId")
        if not video_id:
            continue
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("medium") or thumbnails.get("default") or {}
        try:
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            published = None
        output.append(
            VideoItem(
                video_id=video_id,
                title=snippet.get("title", "(tanpa judul)"),
                description=snippet.get("description", ""),
                thumbnail_url=thumb.get("url"),
                published_at=published,
                privacy_status=item.get("status", {}).get("privacyStatus", "unknown"),
            )
        )
    return VideoPage(videos=output, next_page_token=payload.get("nextPageToken"))


@router.post("/videos", status_code=201)
async def upload_video(
    db: Db,
    video: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=100)],
    description: Annotated[str, Form(max_length=5000)] = "",
    tags: Annotated[str, Form(max_length=1000)] = "",
    privacy_status: Annotated[Literal["private", "unlisted", "public"], Form()] = "private",
) -> UploadResult:
    if not video.filename or not video.content_type or not video.content_type.startswith("video/"):
        raise AppError(422, "Pilih file video dengan tipe MIME video.")
    size = video.size or 0
    if not size or size > MAX_VIDEO_BYTES:
        raise AppError(413, "Ukuran video harus antara 1 byte dan 512 MB.")
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()][:30]
    token, _ = await access_token(db)
    body = {
        "snippet": {"title": title.strip(), "description": description, "tags": tag_list},
        "status": {"privacyStatus": privacy_status},
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, read=120)) as client:
            initiated = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params={"uploadType": "resumable", "part": "snippet,status"},
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Upload-Content-Type": video.content_type,
                    "X-Upload-Content-Length": str(size),
                },
            )
            upload_url = initiated.headers.get("location")
            if initiated.status_code not in (200, 201) or not upload_url:
                raise AppError(502, "YouTube gagal memulai upload.")
            start = 0
            while start < size:
                chunk = await video.read(min(CHUNK_BYTES, size - start))
                if not chunk:
                    raise AppError(422, "File video terputus sebelum upload selesai.")
                end = start + len(chunk) - 1
                uploaded = await client.put(
                    upload_url,
                    content=chunk,
                    headers={
                        "Content-Type": video.content_type,
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end}/{size}",
                    },
                )
                if uploaded.status_code in (200, 201):
                    video_id = uploaded.json().get("id")
                    if not video_id:
                        raise AppError(502, "YouTube tidak mengembalikan ID video.")
                    return UploadResult(video_id=video_id, url=f"https://youtu.be/{video_id}")
                if uploaded.status_code != 308:
                    raise AppError(502, "Upload video ditolak oleh YouTube.")
                start = end + 1
    except AppError:
        raise
    except httpx.HTTPError:
        raise AppError(502, "Koneksi upload ke YouTube terputus. Coba upload kembali.") from None
    raise AppError(502, "YouTube belum menyelesaikan upload video.")
