# author: jf
import json
import mimetypes
import urllib.error
import urllib.request
import uuid


def _normalize_base_url(base_url: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    return cleaned or "https://api.openai.com"


def _normalize_path(path: str, fallback: str) -> str:
    cleaned = (path or "").strip()
    target = cleaned or fallback
    return target if target.startswith("/") else f"/{target}"


def _extract_transcription_text(raw_response: str) -> str:
    cleaned = (raw_response or "").strip()
    if not cleaned:
        return ""

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return cleaned

    if not isinstance(payload, dict):
        return cleaned

    for key in ("text", "transcript", "result"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return cleaned


def _encode_multipart_form_data(
    fields: dict[str, str],
    files: list[tuple[str, str, str, bytes]],
) -> tuple[bytes, str]:
    boundary = f"----resume-builder-{uuid.uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    for field_name, file_name, content_type, content in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_name}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


class OpenAIAudioClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        transcriptions_path: str,
        default_model: str,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        self.api_key = (api_key or "").strip()
        self.transcriptions_path = _normalize_path(transcriptions_path, "/v1/audio/transcriptions")
        self.default_model = (default_model or "").strip() or "gpt-4o-mini-transcribe"

    def transcribe(
        self,
        file_bytes: bytes,
        file_name: str,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> str:
        if not file_bytes:
            raise RuntimeError("audio file cannot be empty")
        if not self.api_key:
            raise RuntimeError("Speech API key is not configured")

        target_model = (model or "").strip() or self.default_model
        target_file_name = (file_name or "").strip() or "audio.webm"
        content_type = mimetypes.guess_type(target_file_name)[0] or "application/octet-stream"

        fields: dict[str, str] = {"model": target_model}
        if (language or "").strip():
            fields["language"] = language.strip()
        if (prompt or "").strip():
            fields["prompt"] = prompt.strip()

        body, content_type_header = _encode_multipart_form_data(
            fields=fields,
            files=[("file", target_file_name, content_type, file_bytes)],
        )

        request = urllib.request.Request(
            url=f"{self.base_url}{self.transcriptions_path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": content_type_header,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw_response = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Speech API HTTP {exc.code}: {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Speech API connection failed: {exc.reason}") from exc

        text = _extract_transcription_text(raw_response)
        if not text:
            raise RuntimeError("Speech provider returned empty transcription")
        return text
