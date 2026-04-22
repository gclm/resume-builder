# author: jf
from collections.abc import Iterator
import logging
import time
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

_LOGGER = logging.getLogger("uvicorn.error")


def _prepare_request_payload(
    request: InterviewTurnRequestDto,
    session_repository: InterviewSessionRepository,
) -> dict[str, Any]:
    prepare_payload_started_at = time.monotonic()
    payload = request.model_dump()
    session_id = str(request.session_id or "").strip()
    if not session_id:
        _LOGGER.warning("[AI面试][流式] payload prepared without sessionId elapsedMs=%s", int((time.monotonic() - prepare_payload_started_at) * 1000))
        return payload

    fetch_session_started_at = time.monotonic()
    stored_session = session_repository.get(session_id)
    fetch_session_elapsed_ms = int((time.monotonic() - fetch_session_started_at) * 1000)
    _LOGGER.warning(
        "[AI面试][流式] session repository get done sessionId=%s elapsedMs=%s found=%s",
        session_id,
        fetch_session_elapsed_ms,
        isinstance(stored_session, dict),
    )
    if not isinstance(stored_session, dict):
        _LOGGER.warning("[AI面试][流式] payload prepared without stored session elapsedMs=%s", int((time.monotonic() - prepare_payload_started_at) * 1000))
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

    _LOGGER.warning(
        "[AI面试][流式] payload prepared from stored session sessionId=%s elapsedMs=%s historySize=%s",
        session_id,
        int((time.monotonic() - prepare_payload_started_at) * 1000),
        len(payload.get("history") or []),
    )
    return payload


def generate_interview_turn_stream(request: InterviewTurnRequestDto) -> Iterator[str]:
    turn_started_at = time.monotonic()
    requested_session_id = str(request.session_id or "").strip() or "-"
    requested_command = str(request.command or "").strip() or "-"
    requested_mode = str(request.mode or "").strip() or "-"
    _LOGGER.warning(
        "[AI面试][流式] request received mode=%s command=%s sessionId=%s",
        requested_mode,
        requested_command,
        requested_session_id,
    )

    settings_started_at = time.monotonic()
    settings = resolve_settings()
    _LOGGER.warning("[AI面试][流式] settings resolved elapsedMs=%s", int((time.monotonic() - settings_started_at) * 1000))

    build_graph_started_at = time.monotonic()
    graph = build_interview_graph(settings)
    _LOGGER.warning("[AI面试][流式] graph built elapsedMs=%s", int((time.monotonic() - build_graph_started_at) * 1000))

    build_repo_started_at = time.monotonic()
    session_repository = build_interview_session_repository(settings)
    _LOGGER.warning("[AI面试][流式] repository built elapsedMs=%s", int((time.monotonic() - build_repo_started_at) * 1000))

    prepare_started_at = time.monotonic()
    request_payload = _prepare_request_payload(request, session_repository)
    _LOGGER.warning(
        "[AI面试][流式] payload ready command=%s historySize=%s",
        request_payload.get("command"),
        len(request_payload.get("history") or []),
    )
    prepared_state = graph.prepare_turn(request_payload)
    prepare_elapsed_ms = int((time.monotonic() - prepare_started_at) * 1000)
    _LOGGER.warning(
        "[AI面试][流式] prepare done mode=%s command=%s sessionId=%s elapsedMs=%s",
        prepared_state.get("mode"),
        prepared_state.get("command"),
        prepared_state.get("sessionId"),
        prepare_elapsed_ms,
    )

    raw_buffer = ""
    last_emitted_reply = ""
    llm_error: str | None = None
    first_token_emitted = False
    stream_chunk_count = 0
    stream_started_at = time.monotonic()

    try:
        _LOGGER.warning("[AI面试][流式] stream start sessionId=%s", prepared_state.get("sessionId"))
        for token in graph.stream_turn_reply(prepared_state):
            if not token:
                continue
            stream_chunk_count += 1
            raw_buffer += token
            assistant_reply = extract_streaming_assistant_reply(raw_buffer)
            if assistant_reply and assistant_reply != last_emitted_reply:
                last_emitted_reply = assistant_reply
                if not first_token_emitted:
                    first_token_emitted = True
                    first_token_elapsed_ms = int((time.monotonic() - stream_started_at) * 1000)
                    _LOGGER.warning(
                        "[AI面试][流式] first token parsed sessionId=%s elapsedMs=%s",
                        prepared_state.get("sessionId"),
                        first_token_elapsed_ms,
                    )
                yield to_interview_chunk_event(assistant_reply)
    except Exception as exc:
        llm_error = f"LLM stream failed: {exc}"
        _LOGGER.warning(
            "[AI面试][流式] stream exception sessionId=%s chunkCount=%s error=%s",
            prepared_state.get("sessionId"),
            stream_chunk_count,
            llm_error,
        )

    stream_elapsed_ms = int((time.monotonic() - stream_started_at) * 1000)
    _LOGGER.warning(
        "[AI面试][流式] stream end sessionId=%s chunkCount=%s rawChars=%s elapsedMs=%s",
        prepared_state.get("sessionId"),
        stream_chunk_count,
        len(raw_buffer),
        stream_elapsed_ms,
    )

    if not raw_buffer.strip():
        _LOGGER.warning(
            "[AI面试][流式] stream ended without payload sessionId=%s error=%s",
            prepared_state.get("sessionId"),
            llm_error or "unknown",
        )
        yield to_interview_error_event(llm_error or "LLM stream returned empty content")
        return

    try:
        finalize_started_at = time.monotonic()
        graph_output = graph.finalize_stream_turn(prepared_state, raw_buffer, llm_error=llm_error)
        finalize_elapsed_ms = int((time.monotonic() - finalize_started_at) * 1000)

        persist_started_at = time.monotonic()
        done_payload = persist_turn_result(request, graph_output, session_repository)
        persist_elapsed_ms = int((time.monotonic() - persist_started_at) * 1000)
        final_reply = str(done_payload.get("assistantReply") or "")

        if final_reply and final_reply != last_emitted_reply:
            yield to_interview_chunk_event(final_reply)

        total_elapsed_ms = int((time.monotonic() - turn_started_at) * 1000)
        _LOGGER.warning(
            "[AI面试][流式] turn done sessionId=%s finalizeMs=%s persistMs=%s totalMs=%s",
            prepared_state.get("sessionId"),
            finalize_elapsed_ms,
            persist_elapsed_ms,
            total_elapsed_ms,
        )
        yield to_interview_done_event(done_payload)
    except Exception as exc:  # pragma: no cover
        _LOGGER.warning("[AI面试][流式] finalize exception sessionId=%s error=%s", prepared_state.get("sessionId"), exc)
        yield to_interview_error_event(str(exc))
