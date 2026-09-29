import hashlib

from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.core.config import get_settings

SESSION_SECONDS = 12 * 60 * 60
STATE_SECONDS = 10 * 60


def signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        get_settings().app_secret_key.get_secret_value(), salt="qa-report-v1"
    )


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def read_cookie(cookie: str | None) -> str | None:
    if not cookie:
        return None
    try:
        token = signer().loads(cookie, max_age=SESSION_SECONDS)
        return token_digest(token) if isinstance(token, str) else None
    except BadSignature:
        return None


def sign_state(state: str) -> str:
    return signer().dumps({"state": state, "kind": "google-oauth"})


def read_state(value: str | None) -> str | None:
    if not value:
        return None
    try:
        payload = signer().loads(value, max_age=STATE_SECONDS)
        return payload.get("state") if isinstance(payload, dict) else None
    except (BadSignature, AttributeError):
        return None
