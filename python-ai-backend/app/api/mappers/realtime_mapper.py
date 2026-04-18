# author: jf
from app.api.schemas.realtime import RealtimeClientSecretRequest, RealtimeClientSecretResponse
from app.application.dto.realtime_dto import RealtimeClientSecretRequestDto, RealtimeClientSecretResponseDto


def realtime_request_to_dto(request: RealtimeClientSecretRequest | None) -> RealtimeClientSecretRequestDto:
    if request is None:
        return RealtimeClientSecretRequestDto()
    return RealtimeClientSecretRequestDto(model=request.model, language=request.language)


def realtime_response_from_dto(response: RealtimeClientSecretResponseDto) -> RealtimeClientSecretResponse:
    return RealtimeClientSecretResponse(
        clientSecret=response.client_secret,
        expiresAt=response.expires_at,
        model=response.model,
        realtimeApiBaseUrl=response.realtime_api_base_url,
        realtimeCallsPath=response.realtime_calls_path,
    )
