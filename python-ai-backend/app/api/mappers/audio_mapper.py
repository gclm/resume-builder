# author: jf
from app.api.schemas.audio import AudioTranscriptionResponse
from app.application.dto.audio_dto import AudioTranscriptionRequestDto, AudioTranscriptionResponseDto


def audio_request_to_dto(
    *,
    file_bytes: bytes,
    file_name: str,
    model: str | None,
    language: str | None,
    prompt: str | None,
) -> AudioTranscriptionRequestDto:
    return AudioTranscriptionRequestDto(
        file_bytes=file_bytes,
        file_name=file_name,
        model=model,
        language=language,
        prompt=prompt,
    )


def audio_response_from_dto(response: AudioTranscriptionResponseDto) -> AudioTranscriptionResponse:
    return AudioTranscriptionResponse(text=response.text)
