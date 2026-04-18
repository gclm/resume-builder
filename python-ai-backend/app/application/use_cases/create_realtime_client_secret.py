# author: jf
from app.application.dto.realtime_dto import RealtimeClientSecretRequestDto, RealtimeClientSecretResponseDto
from app.bootstrap.container import build_realtime_client


def create_realtime_client_secret(request: RealtimeClientSecretRequestDto) -> RealtimeClientSecretResponseDto:
    client = build_realtime_client()
    response_payload = client.create_client_secret(model=request.model, language=request.language)
    return RealtimeClientSecretResponseDto(
        client_secret=str(response_payload.get("clientSecret") or ""),
        expires_at=response_payload.get("expiresAt"),
        model=str(response_payload.get("model") or ""),
        realtime_api_base_url=str(response_payload.get("realtimeApiBaseUrl") or ""),
        realtime_calls_path=str(response_payload.get("realtimeCallsPath") or ""),
    )
