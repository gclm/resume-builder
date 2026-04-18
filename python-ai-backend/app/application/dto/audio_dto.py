# author: jf
from dataclasses import dataclass


@dataclass(slots=True)
class AudioTranscriptionRequestDto:
    file_bytes: bytes
    file_name: str
    model: str | None = None
    language: str | None = None
    prompt: str | None = None


@dataclass(slots=True)
class AudioTranscriptionResponseDto:
    text: str
