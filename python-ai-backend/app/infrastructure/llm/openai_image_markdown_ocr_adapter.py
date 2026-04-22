# author: jf
import base64
from time import perf_counter
from urllib.parse import urlsplit, urlunsplit

from app.domain.exceptions.rag_exceptions import ImageOcrError


def _guess_media_type(content_type: str | None, file_name: str) -> str:
    normalized = (content_type or "").strip().lower()
    if normalized:
        return normalized
    suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }.get(suffix, "application/octet-stream")


class OpenAIImageMarkdownOcrAdapter:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        detail: str,
        base_url: str | None = None,
        timeout_seconds: float = 40.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model_name = (model_name or "").strip() or "gpt-4.1"
        self.detail = (detail or "").strip() or "high"
        self.base_url = (base_url or "").strip() or None
        self.timeout_seconds = self._normalize_timeout(timeout_seconds)

    def extract_markdown(
        self,
        image_bytes: bytes,
        file_name: str,
        content_type: str | None = None,
    ) -> str:
        if not image_bytes:
            raise ImageOcrError("Image file cannot be empty")
        if not self.api_key:
            raise ImageOcrError("OPENAI_API_KEY is not configured")

        # This adapter now has a single responsibility: send the OCR request through
        # the official OpenAI Python SDK and return the extracted text as plain text.
        data_url = self._to_data_url(image_bytes=image_bytes, file_name=file_name, content_type=content_type)
        normalized_base_url = self._normalize_api_base_url(self.base_url)
        prompt = (
            "你是严格的 OCR 文字提取助手。"
            "请只提取图片中清晰可见的文字内容。"
            "不要猜测、补全或编造缺失内容。"
            "只返回纯文本，不要返回 Markdown、代码块、列表标记或任何额外说明。"
        )

        _log_image_ocr(
            "ocr_started",
            base_url=self.base_url or "https://api.openai.com",
            normalized_base_url=normalized_base_url,
            model=self.model_name,
            api_key=_mask_api_key(self.api_key),
            timeout_seconds=self.timeout_seconds,
            file_name=file_name,
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": self.detail}},
                ],
            }
        ]

        started = perf_counter()
        try:
            markdown = self._extract_text_with_openai_sdk(messages=messages, base_url=normalized_base_url)
        except Exception as exc:
            _log_image_ocr(
                "sdk_failed",
                elapsed_ms=f"{(perf_counter() - started) * 1000:.1f}",
                error=exc,
            )
            if isinstance(exc, ImageOcrError):
                raise
            raise ImageOcrError(f"OCR request failed: {exc}") from exc

        if markdown:
            _log_image_ocr("sdk_success", elapsed_ms=f"{(perf_counter() - started) * 1000:.1f}")
            return markdown

        _log_image_ocr("sdk_empty_content", elapsed_ms=f"{(perf_counter() - started) * 1000:.1f}")
        raise ImageOcrError("OCR returned no usable text content")

    @staticmethod
    def _to_data_url(image_bytes: bytes, file_name: str, content_type: str | None = None) -> str:
        media_type = _guess_media_type(content_type=content_type, file_name=file_name)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{media_type};base64,{encoded}"

    @staticmethod
    def _extract_text_from_chat_payload(data: object) -> str:
        if hasattr(data, "model_dump"):
            dumped = data.model_dump(mode="python")
            if isinstance(dumped, dict):
                data = dumped

        if not isinstance(data, dict):
            return ""

        choices = data.get("choices") or []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                text = content.strip()
                if text:
                    return text
            elif isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    text = str(item.get("text") or "").strip()
                    if text:
                        return text
        return ""

    def _extract_text_with_openai_sdk(self, messages: list[dict], base_url: str) -> str:
        try:
            from openai import OpenAI
        except Exception as exc:
            raise ImageOcrError(f"OpenAI SDK unavailable: {exc}") from exc

        _log_image_ocr("sdk_client_init_started", normalized_base_url=base_url, model=self.model_name)
        client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=self.timeout_seconds,
            max_retries=0,
        )
        _log_image_ocr("sdk_client_init_finished", normalized_base_url=base_url, model=self.model_name)
        _log_image_ocr("sdk_request_started", normalized_base_url=base_url, model=self.model_name)
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )
        _log_image_ocr("sdk_request_finished", normalized_base_url=base_url, model=self.model_name)
        return self._extract_text_from_chat_payload(response)

    @staticmethod
    def _normalize_timeout(raw_timeout: float) -> float:
        try:
            normalized = float(raw_timeout)
        except (TypeError, ValueError):
            return 40.0
        return max(3.0, normalized)

    @staticmethod
    def _normalize_api_base_url(base_url: str | None) -> str:
        raw = (base_url or "").strip() or "https://api.openai.com"
        parsed = urlsplit(raw)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc
        path = parsed.path.rstrip("/")

        if not netloc:
            raise ImageOcrError(f"Invalid OpenAI base_url: {raw}")

        if not path:
            path = "/v1"
        elif not path.endswith("/v1"):
            path = f"{path}/v1"

        return urlunsplit((scheme, netloc, path, parsed.query, parsed.fragment)).rstrip("/")


def _mask_api_key(api_key: str) -> str:
    safe = (api_key or "").strip()
    if not safe:
        return ""
    if len(safe) <= 6:
        return safe[:3] + "***"
    return f"{safe[:3]}***{safe[-4:]}"


def _log_image_ocr(message: str, **extra: object) -> None:
    parts = [f"[knowledge-upload][ImageOCR] {message}"]
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), flush=True)
