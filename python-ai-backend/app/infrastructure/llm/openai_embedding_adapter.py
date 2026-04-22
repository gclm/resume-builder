# author: jf
from app.domain.exceptions.rag_exceptions import EmbeddingError

_LLAMA_INDEX_SUPPORTED_OPENAI_EMBEDDING_MODELS = frozenset(
    {
        "davinci",
        "curie",
        "babbage",
        "ada",
        "text-embedding-ada-002",
        "text-embedding-3-large",
        "text-embedding-3-small",
    }
)
_LLAMA_INDEX_FALLBACK_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingAdapter:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model_name = (model_name or "").strip() or "text-embedding-3-small"
        self.base_url = (base_url or "").strip() or None
        self.timeout_seconds = self._normalize_timeout(timeout_seconds)
        self.provider_name = "openai"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        # 业务入口意图：把上游切好的 chunk 文本批量向量化，供知识库入库和检索链路复用。
        safe_texts = [text.strip() for text in texts if (text or "").strip()]
        if not safe_texts:
            _log_embedding("跳过调用，输入为空")
            return []
        if not self.api_key:
            raise EmbeddingError("OPENAI_API_KEY 未配置，无法生成 Embedding")

        # 关键步骤：统一通过 llama_index 的 OpenAIEmbedding 适配器发起请求，
        # 让 application/domain 不直接绑定具体 SDK，同时在这里兜住第三方兼容网关差异。
        client = self._create_client()
        try:
            vectors = client.get_text_embedding_batch(safe_texts)
        except Exception as exc:
            raise EmbeddingError(
                f"OpenAI Embedding 调用失败（provider=openai, model={self.model_name}, timeout={self.timeout_seconds}s）：{exc}"
            ) from exc

        # 关键分支：返回向量数量必须与输入文本数量一致，否则上游无法安全写入 pgvector。
        if len(vectors) != len(safe_texts):
            raise EmbeddingError("Embedding 返回数量与输入数量不一致")

        return [self._normalize_vector(vector) for vector in vectors]

    def _create_client(self):
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
        except ImportError as exc:
            raise EmbeddingError("缺少 llama_index.embeddings.openai 依赖，无法生成 Embedding") from exc

        # 边界职责：适配器层负责把仓库配置映射为三方库参数，
        # 并在真正创建客户端前处理 llama_index 对模型枚举的限制。
        kwargs = self._build_client_kwargs()
        _log_embedding(
            "创建 OpenAIEmbedding 客户端",
            provider=self.provider_name,
            model=self.model_name,
            base_url=self.base_url or "default",
            timeout_seconds=self.timeout_seconds,
        )
        return OpenAIEmbedding(**kwargs)

    def _build_client_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "model": self.model_name,
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
            "max_retries": 0,
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url

        # 关键分支：阿里百炼等 OpenAI 兼容网关经常使用自定义 embedding model id。
        # llama_index 会先校验 `model` 是否属于内置枚举，这会让请求在真正发到上游前就失败。
        # 这里先传一个合法占位模型，再用 `model_name` 覆盖最终请求的模型名，以兼容自定义 id。
        if self.model_name not in _LLAMA_INDEX_SUPPORTED_OPENAI_EMBEDDING_MODELS:
            kwargs["model"] = _LLAMA_INDEX_FALLBACK_EMBEDDING_MODEL
            kwargs["model_name"] = self.model_name
            _log_embedding(
                "检测到自定义 OpenAI 兼容 embedding 模型，启用 llama_index 兼容模式",
                requested_model=self.model_name,
                fallback_model=_LLAMA_INDEX_FALLBACK_EMBEDDING_MODEL,
            )

        return kwargs

    @staticmethod
    def _normalize_timeout(raw_timeout: float) -> float:
        try:
            normalized = float(raw_timeout)
        except (TypeError, ValueError):
            return 45.0
        return max(1.0, normalized)

    @staticmethod
    def _normalize_vector(raw_vector: list[float]) -> list[float]:
        if not isinstance(raw_vector, list) or not raw_vector:
            raise EmbeddingError("Embedding 向量为空或格式非法")
        try:
            return [float(value) for value in raw_vector]
        except (TypeError, ValueError) as exc:
            raise EmbeddingError("Embedding 向量包含无法转换为 float 的值") from exc


def _log_embedding(message: str, **extra: object) -> None:
    parts = [f"[知识库上传][EmbeddingAdapter] {message}"]
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), flush=True)
