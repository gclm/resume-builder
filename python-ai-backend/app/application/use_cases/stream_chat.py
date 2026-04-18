# author: jf
from collections.abc import Iterator

from app.application.dto.chat_dto import ChatRequestDto
from app.domain.policies.sanitize_policy import sanitize_resume_markdown
from app.domain.services.resume_section_clean_service import contains_only_section_headings
from app.infrastructure.factories.llm_factory import create_chat_client
from app.shared.streaming.sse import to_sse


def generate_chat_stream(request: ChatRequestDto) -> Iterator[str]:
    client = create_chat_client()

    try:
        if not request.sanitize_output:
            for chunk in client.stream_chat(message=request.message):
                if not chunk:
                    continue
                yield to_sse("chunk", chunk)
            return

        raw_buffer = ""
        emitted_length = 0

        for chunk in client.stream_chat(message=request.message):
            if not chunk:
                continue
            raw_buffer += chunk
            sanitized = sanitize_resume_markdown(raw_buffer)
            stable_end = sanitized.rfind("\n")
            if stable_end < 0:
                continue
            emit_until = stable_end + 1
            if emit_until > emitted_length:
                delta = sanitized[emitted_length:emit_until]
                if contains_only_section_headings(delta):
                    continue
                yield to_sse("chunk", delta)
                emitted_length = emit_until

        sanitized = sanitize_resume_markdown(raw_buffer)
        if len(sanitized) > emitted_length:
            tail = sanitized[emitted_length:]
            if not contains_only_section_headings(tail):
                yield to_sse("chunk", tail)
    except Exception as exc:  # pragma: no cover
        yield to_sse("error", str(exc))
