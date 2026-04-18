# author: jf
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DOTENV_LOADED = False


def _load_local_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    env_file = Path(__file__).resolve().parents[3] / ".env"
    if not env_file.exists():
        _DOTENV_LOADED = True
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())

    _DOTENV_LOADED = True


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_first_non_empty(*names: str, default: str = "") -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    server_port: int
    app_cors_allowed_origins: str
    app_rag_top_k: int
    openai_base_url: str
    openai_api_key: str
    openai_chat_model: str
    openai_chat_completions_path: str
    openai_speech_base_url: str
    openai_speech_api_key: str
    openai_speech_transcriptions_path: str
    openai_speech_transcription_model: str
    openai_realtime_base_url: str
    openai_realtime_api_key: str
    openai_realtime_client_secrets_path: str
    openai_realtime_calls_path: str
    openai_realtime_transcription_model: str
    openai_realtime_language: str
    mysql_datasource_url: str
    mysql_datasource_username: str
    mysql_datasource_password: str
    pgvector_datasource_url: str
    autogen_enabled: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_local_dotenv()
    openai_base_url = _get_first_non_empty("OPENAI_CHAT_BASE_URL", "OPENAI_BASE_URL", default="https://api.openai.com")
    openai_api_key = _get_first_non_empty("OPENAI_CHAT_API_KEY", "OPENAI_API_KEY")
    return Settings(
        server_port=_get_int("SERVER_PORT", 8999),
        app_cors_allowed_origins=os.getenv("APP_CORS_ALLOWED_ORIGINS", "http://localhost:5173"),
        app_rag_top_k=_get_int("APP_RAG_TOP_K", 5),
        openai_base_url=openai_base_url,
        openai_api_key=openai_api_key,
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4"),
        openai_chat_completions_path=os.getenv("OPENAI_CHAT_COMPLETIONS_PATH", "/v1/chat/completions"),
        openai_speech_base_url=_get_first_non_empty("OPENAI_SPEECH_BASE_URL", "OPENAI_BASE_URL", default=openai_base_url),
        openai_speech_api_key=_get_first_non_empty("OPENAI_SPEECH_API_KEY", "OPENAI_API_KEY", default=openai_api_key),
        openai_speech_transcriptions_path=os.getenv("OPENAI_SPEECH_TRANSCRIPTIONS_PATH", "/v1/audio/transcriptions"),
        openai_speech_transcription_model=os.getenv("OPENAI_SPEECH_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe"),
        openai_realtime_base_url=_get_first_non_empty("OPENAI_REALTIME_BASE_URL", "OPENAI_SPEECH_BASE_URL", "OPENAI_BASE_URL", default=openai_base_url),
        openai_realtime_api_key=_get_first_non_empty("OPENAI_REALTIME_API_KEY", "OPENAI_SPEECH_API_KEY", "OPENAI_API_KEY", default=openai_api_key),
        openai_realtime_client_secrets_path=os.getenv("OPENAI_REALTIME_CLIENT_SECRETS_PATH", "/v1/realtime/client_secrets"),
        openai_realtime_calls_path=os.getenv("OPENAI_REALTIME_CALLS_PATH", "/v1/realtime/calls"),
        openai_realtime_transcription_model=os.getenv("OPENAI_REALTIME_TRANSCRIPTION_MODEL", "gpt-4o-transcribe"),
        openai_realtime_language=os.getenv("OPENAI_REALTIME_LANGUAGE", "zh"),
        mysql_datasource_url=os.getenv("MYSQL_DATASOURCE_URL", ""),
        mysql_datasource_username=os.getenv("MYSQL_DATASOURCE_USERNAME", ""),
        mysql_datasource_password=os.getenv("MYSQL_DATASOURCE_PASSWORD", ""),
        pgvector_datasource_url=os.getenv("PGVECTOR_DATASOURCE_URL", ""),
        autogen_enabled=os.getenv("AUTOGEN_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
    )
