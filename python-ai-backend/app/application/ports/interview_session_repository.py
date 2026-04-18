# author: jf
from typing import Any, Protocol


class InterviewSessionRepository(Protocol):
    def get(self, session_id: str) -> dict[str, Any] | None: ...

    def save(self, session_id: str, session: dict[str, Any]) -> None: ...

    def list(self, limit: int) -> list[dict[str, Any]]: ...
