# author: jf
from fastapi import APIRouter, File, Form, UploadFile

from app.api.mappers.audio_mapper import audio_request_to_dto, audio_response_from_dto
from app.api.schemas.audio import AudioTranscriptionResponse
from app.application.use_cases.transcribe_audio import transcribe_audio as transcribe_audio_use_case

router = APIRouter(prefix="/api/ai", tags=["ai-audio"])


@router.post("/audio/transcriptions", response_model=AudioTranscriptionResponse)
async def transcribe_audio_route(
    file: UploadFile = File(...),
    model: str | None = Form(default=None),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
) -> AudioTranscriptionResponse:
    content = await file.read()
    return audio_response_from_dto(
        transcribe_audio_use_case(
            audio_request_to_dto(
                file_bytes=content,
                file_name=file.filename or "audio.webm",
                model=model,
                language=language,
                prompt=prompt,
            )
        )
    )
