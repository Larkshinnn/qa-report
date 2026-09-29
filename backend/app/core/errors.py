from uuid import UUID

from pydantic import BaseModel


class ErrorBody(BaseModel):
    detail: str
    existing_id: UUID | None = None


class AppError(Exception):
    def __init__(self, status: int, detail: str, existing_id: UUID | None = None) -> None:
        self.status = status
        self.body = ErrorBody(detail=detail, existing_id=existing_id)
