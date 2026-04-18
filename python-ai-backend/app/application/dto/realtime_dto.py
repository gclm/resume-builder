# author: jf
from dataclasses import dataclass


@dataclass(slots=True)
class RealtimeClientSecretRequestDto:
    model: str | None = None
    language: str | None = None


@dataclass(slots=True)
class RealtimeClientSecretResponseDto:
    client_secret: str
    model: str
    realtime_api_base_url: str
    realtime_calls_path: str
    expires_at: int | None = None
