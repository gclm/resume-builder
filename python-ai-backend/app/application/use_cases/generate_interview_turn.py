# author: jf
from collections.abc import Iterator
from typing import Any

from app.application.dto.interview_dto import InterviewTurnRequestDto
from app.application.ports.interview_session_repository import InterviewSessionRepository
from app.application.services.interview_session_service import persist_turn_result
from app.application.services.response_stream_service import (
    extract_streaming_assistant_reply,
    to_interview_chunk_event,
    to_interview_done_event,
    to_interview_error_event,
)
from app.bootstrap.container import build_interview_graph, build_interview_session_repository, resolve_settings


def _prepare_request_payload(
    request: InterviewTurnRequestDto,
    session_repository: InterviewSessionRepository,
) -> dict[str, Any]:
    payload = request.model_dump()
    session_id = str(request.session_id or "").strip()
    if not session_id:
        return payload

    stored_session = session_repository.get(session_id)
    if not isinstance(stored_session, dict):
        return payload

    request_history = payload.get("history")
    safe_request_history = request_history if isinstance(request_history, list) else []
    stored_messages = stored_session.get("messages")
    safe_stored_messages = stored_messages if isinstance(stored_messages, list) else []

    if len(safe_request_history) < len(safe_stored_messages):
        payload["history"] = safe_stored_messages

    if not str(payload.get("memorySummary") or "").strip():
        payload["memorySummary"] = stored_session.get("memorySummary") or ""

    if not payload.get("resumeSnapshot"):
        payload["resumeSnapshot"] = stored_session.get("resumeSnapshot") or {}

    if not payload.get("mode"):
        payload["mode"] = stored_session.get("mode") or payload.get("mode")

    return payload


def generate_interview_turn_stream(request: InterviewTurnRequestDto) -> Iterator[str]:
    settings = resolve_settings()
    graph = build_interview_graph(settings)
    session_repository = build_interview_session_repository(settings)
    prepared_state = graph.prepare_turn(_prepare_request_payload(request, session_repository))

    raw_buffer = ""
    last_emitted_reply = ""
    llm_error: str | None = None

    try:
        for token in graph.stream_turn_reply(prepared_state):
            if not token:
                continue
            raw_buffer += token
            assistant_reply = extract_streaming_assistant_reply(raw_buffer)
            if assistant_reply and assistant_reply != last_emitted_reply:
                last_emitted_reply = assistant_reply
                yield to_interview_chunk_event(assistant_reply)
    except Exception as exc:
        llm_error = f"LLM stream failed: {exc}"

    if not raw_buffer.strip():
        yield to_interview_error_event(llm_error or "LLM stream returned empty content")
        return

    try:
        graph_output = graph.finalize_stream_turn(prepared_state, raw_buffer, llm_error=llm_error)
        done_payload = persist_turn_result(request, graph_output, session_repository)
        final_reply = str(done_payload.get("assistantReply") or "")

        if final_reply and final_reply != last_emitted_reply:
            yield to_interview_chunk_event(final_reply)

        yield to_interview_done_event(done_payload)
    except Exception as exc:  # pragma: no cover
        yield to_interview_error_event(str(exc))
