# author: jf
from app.application.dto.chat_dto import ChatRequestDto, ChatResponseDto
from app.domain.policies.sanitize_policy import safe_content, sanitize_resume_markdown
from app.infrastructure.factories.llm_factory import create_chat_client


def run_chat(request: ChatRequestDto) -> ChatResponseDto:
    client = create_chat_client()
    output = client.chat(message=request.message)
    safe_output = safe_content(output)
    if request.sanitize_output:
        safe_output = sanitize_resume_markdown(safe_output)
    return ChatResponseDto(answer=safe_output)
