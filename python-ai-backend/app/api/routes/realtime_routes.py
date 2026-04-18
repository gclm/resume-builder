# author: jf
from fastapi import APIRouter

from app.api.mappers.realtime_mapper import realtime_request_to_dto, realtime_response_from_dto
from app.api.schemas.realtime import RealtimeClientSecretRequest, RealtimeClientSecretResponse
from app.application.use_cases.create_realtime_client_secret import (
    create_realtime_client_secret as create_realtime_client_secret_use_case,
)

router = APIRouter(prefix="/api/ai", tags=["ai-realtime"])


@router.post("/realtime/client-secret", response_model=RealtimeClientSecretResponse)
def create_realtime_client_secret_route(
    request: RealtimeClientSecretRequest | None = None,
) -> RealtimeClientSecretResponse:
    return realtime_response_from_dto(
        create_realtime_client_secret_use_case(realtime_request_to_dto(request))
    )
