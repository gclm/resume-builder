# author: jf
from app.application.dto.audio_dto import AudioTranscriptionRequestDto, AudioTranscriptionResponseDto
from app.bootstrap.container import build_audio_client


def transcribe_audio(request: AudioTranscriptionRequestDto) -> AudioTranscriptionResponseDto:
    client = build_audio_client()
    text = client.transcribe(
        file_bytes=request.file_bytes,
        file_name=request.file_name,
        model=request.model,
        language=request.language,
        prompt=request.prompt,
    )
    return AudioTranscriptionResponseDto(text=text)
