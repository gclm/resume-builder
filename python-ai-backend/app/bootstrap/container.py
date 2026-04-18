# author: jf
from app.application.ports.agent_runtime_port import AgentRuntimePort
from app.application.ports.interview_session_repository import InterviewSessionRepository
from app.application.ports.llm_port import ChatClientPort
from app.application.ports.vector_store_port import VectorStorePort
from app.domain.services.interview_flow_service import InterviewGraph
from app.domain.services.rag_retrieval_service import RagRetrieverService
from app.infrastructure.agents.autogen_runtime_adapter import AutoGenAgentRuntimeAdapter
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.factories.llm_factory import create_audio_client, create_chat_client, create_realtime_client
from app.infrastructure.persistence.mysql.session_repository import MySqlInterviewSessionRepository
from app.infrastructure.persistence.pgvector.vector_store_adapter import PgVectorStoreAdapter


def resolve_settings() -> Settings:
    return get_settings()


def build_chat_client(settings: Settings | None = None) -> ChatClientPort:
    return create_chat_client(settings)


def build_audio_client(settings: Settings | None = None):
    return create_audio_client(settings)


def build_realtime_client(settings: Settings | None = None):
    return create_realtime_client(settings)


def build_vector_store(settings: Settings | None = None) -> VectorStorePort:
    resolved = settings or get_settings()
    return PgVectorStoreAdapter(connection_url=resolved.pgvector_datasource_url)


def build_rag_retriever(settings: Settings | None = None) -> RagRetrieverService:
    return RagRetrieverService(vector_store=build_vector_store(settings))


def build_agent_runtime(settings: Settings | None = None) -> AgentRuntimePort:
    resolved = settings or get_settings()
    return AutoGenAgentRuntimeAdapter(enabled=resolved.autogen_enabled)


def build_interview_session_repository(settings: Settings | None = None) -> InterviewSessionRepository:
    resolved = settings or get_settings()
    return MySqlInterviewSessionRepository(
        datasource_url=resolved.mysql_datasource_url,
        username=resolved.mysql_datasource_username,
        password=resolved.mysql_datasource_password,
    )


def build_interview_graph(settings: Settings | None = None) -> InterviewGraph:
    resolved = settings or get_settings()
    return InterviewGraph(
        llm_client=build_chat_client(resolved),
        rag_retriever=build_rag_retriever(resolved),
        autogen_runtime=build_agent_runtime(resolved),
    )
