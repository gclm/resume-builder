# author: jf
from typing import Protocol


class AudioTranscriptionPort(Protocol):
    def transcribe(
        self,
        file_bytes: bytes,
        file_name: str,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> str: ...
