import secrets
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import User
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.models import Account, YouTubeConnection
from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    read_state,
    read_state_subject,
    sign_state,
)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
Db = Annotated[AsyncSession, Depends(get_db)]
STATE_COOKIE = "qa_report_youtube_state"
UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
READ_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
# Needed for videos.update / videos.delete; existing connections must reconnect once.
MANAGE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
MAX_LIST_PAGES = 20  # 50 videos per page -> up to 1000 videos
VideoId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{6,20}$")]
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


class VideoList(BaseModel):
    videos: list[VideoItem]
    truncated: bool = False


class VideoUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)
    privacy_status: Literal["private", "unlisted", "public"]


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


def google_error(response: httpx.Response, fallback: str) -> AppError:
    try:
        error = response.json().get("error", {})
    except ValueError:
        error = {}
    if not isinstance(error, dict):
        error = {}
    reasons = {entry.get("reason") for entry in error.get("errors", []) if isinstance(entry, dict)}
    if response.status_code == 403 and (
        reasons & {"insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}
        or "insufficient" in str(error.get("message", "")).lower()
    ):
        return AppError(
            403,
            "Izin edit/hapus video belum diberikan. "
            "Admin perlu menghubungkan ulang channel YouTube.",
        )
    if response.status_code == 404:
        return AppError(404, "Video tidak ditemukan di channel bersama.")
    if response.status_code == 403:
        return AppError(403, "YouTube menolak aksi ini untuk video tersebut.")
    return AppError(502, fallback)


def parse_published(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def thumbnail(snippet: dict[str, Any]) -> str | None:
    thumbnails = snippet.get("thumbnails", {})
    return (thumbnails.get("medium") or thumbnails.get("default") or {}).get("url")


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
    state = sign_state(secrets.token_urlsafe(32), str(user.id))
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.youtube_redirect_uri,
            "response_type": "code",
            "scope": f"{UPLOAD_SCOPE} {READ_SCOPE} {MANAGE_SCOPE}",
            "state": state,
            "access_type": "offline",
            "prompt": "consent select_account",
            "include_granted_scopes": "true",
        }
    )
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302
    )


@router.get("/callback")
async def callback(
    db: Db,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    settings = get_settings()
    if error or not code or not read_state(state):
        raise AppError(400, "Koneksi YouTube dibatalkan atau tidak valid.")
    try:
        initiator_id = UUID(read_state_subject(state) or "")
    except ValueError:
        raise AppError(400, "Koneksi YouTube dibatalkan atau tidak valid.") from None
    initiator = await db.get(Account, initiator_id)
    if initiator is None or not is_admin(initiator):
        raise AppError(400, "Koneksi YouTube dibatalkan atau tidak valid.")
    initiator_email = initiator.email
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
            connected_by=initiator_email,
        )
        db.add(current)
    else:
        current.channel_id = channel["id"]
        current.uploads_playlist_id = uploads_playlist_id
        current.channel_title = channel["snippet"]["title"]
        current.refresh_token_encrypted = encrypt_secret(refresh)
        current.connected_by = initiator_email
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
async def videos(_user: User, db: Db) -> VideoList:
    """Return every upload so the client can search, filter and paginate locally."""
    token, linked = await access_token(db)
    output: list[VideoItem] = []
    page_token: str | None = None
    truncated = False
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(MAX_LIST_PAGES):
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
                if response.status_code != 200:
                    raise AppError(502, "YouTube menolak permintaan daftar konten.")
                payload = response.json()
                for item in payload.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("contentDetails", {}).get("videoId")
                    if not video_id:
                        continue
                    output.append(
                        VideoItem(
                            video_id=video_id,
                            title=snippet.get("title", "(tanpa judul)"),
                            description=snippet.get("description", ""),
                            thumbnail_url=thumbnail(snippet),
                            published_at=parse_published(snippet.get("publishedAt")),
                            privacy_status=item.get("status", {}).get("privacyStatus", "unknown"),
                        )
                    )
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break
                truncated = page == MAX_LIST_PAGES - 1
    except AppError:
        raise
    except httpx.HTTPError:
        raise AppError(502, "Daftar konten YouTube tidak dapat dimuat.") from None
    return VideoList(videos=output, truncated=truncated)


@router.put("/videos/{video_id}")
async def update_video(_user: User, db: Db, video_id: VideoId, body: VideoUpdate) -> VideoItem:
    token, _ = await access_token(db)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            current = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet,status", "id": video_id},
                headers=headers,
            )
            if current.status_code != 200:
                raise google_error(current, "Data video tidak dapat dimuat dari YouTube.")
            items = current.json().get("items", [])
            if not items:
                raise AppError(404, "Video tidak ditemukan di channel bersama.")
            snippet = items[0].get("snippet", {})
            status_part = items[0].get("status", {})
            # videos.update clears omitted writable fields, so carry the existing ones over.
            new_snippet = {
                key: snippet[key]
                for key in ("categoryId", "tags", "defaultLanguage", "defaultAudioLanguage")
                if key in snippet
            }
            new_snippet.update(title=body.title.strip(), description=body.description)
            new_status = {
                key: status_part[key]
                for key in (
                    "embeddable",
                    "license",
                    "publicStatsViewable",
                    "selfDeclaredMadeForKids",
                    "containsSyntheticMedia",
                )
                if key in status_part
            }
            new_status["privacyStatus"] = body.privacy_status
            if body.privacy_status == "private" and status_part.get("publishAt"):
                new_status["publishAt"] = status_part["publishAt"]
            updated = await client.put(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet,status"},
                json={"id": video_id, "snippet": new_snippet, "status": new_status},
                headers=headers,
            )
    except AppError:
        raise
    except httpx.HTTPError:
        raise AppError(502, "Google tidak dapat dihubungi. Coba lagi.") from None
    if updated.status_code != 200:
        raise google_error(updated, "YouTube gagal menyimpan perubahan video.")
    payload = updated.json()
    result = payload.get("snippet") or snippet
    return VideoItem(
        video_id=video_id,
        title=result.get("title", body.title.strip()),
        description=result.get("description", body.description),
        thumbnail_url=thumbnail(result) or thumbnail(snippet),
        published_at=parse_published(result.get("publishedAt") or snippet.get("publishedAt")),
        privacy_status=payload.get("status", {}).get("privacyStatus", body.privacy_status),
    )


@router.delete("/videos/{video_id}", status_code=204)
async def delete_video(_user: User, db: Db, video_id: VideoId) -> None:
    token, _ = await access_token(db)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"id": video_id},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        raise AppError(502, "Google tidak dapat dihubungi. Coba lagi.") from None
    if response.status_code != 204:
        raise google_error(response, "YouTube gagal menghapus video.")


@router.post("/videos", status_code=201)
async def upload_video(
    _user: User,
    db: Db,
    video: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=100)],
    description: Annotated[str, Form(max_length=5000)] = "",
    privacy_status: Annotated[Literal["private", "unlisted", "public"], Form()] = "private",
) -> UploadResult:
    if not video.filename or not video.content_type or not video.content_type.startswith("video/"):
        raise AppError(422, "Pilih file video dengan tipe MIME video.")
    size = video.size or 0
    if not size or size > MAX_VIDEO_BYTES:
        raise AppError(413, "Ukuran video harus antara 1 byte dan 512 MB.")
    token, _ = await access_token(db)
    body = {
        "snippet": {"title": title.strip(), "description": description},
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
