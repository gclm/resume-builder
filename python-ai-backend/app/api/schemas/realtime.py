# author: jf
from pydantic import BaseModel


class RealtimeClientSecretRequest(BaseModel):
    model: str | None = None
    language: str | None = None


class RealtimeClientSecretResponse(BaseModel):
    clientSecret: str
    expiresAt: int | None = None
    model: str
    realtimeApiBaseUrl: str
    realtimeCallsPath: str

