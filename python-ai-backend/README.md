<!-- author: jf -->
# python-ai-backend

基于 FastAPI 的 Python AI 后端，实现了与前端现有接口契约兼容的聊天、流式输出、AI 面试、会话存储、RAG、语音转写与 Realtime 临时密钥能力。

## 作用说明

- 对外继续提供 `'/api/ai/*'` 风格接口，前端无需切换请求路径。
- AI 面试会话与消息历史存储到 MySQL。
- RAG 文档向量检索使用 PostgreSQL + pgvector。
- 提供普通问答和流式问答，便于替代或并行参考 Spring AI 后端实现。

## 快速启动

### 前置依赖

- Python `3.11+`
- `uv`
- MySQL + PostgreSQL + pgvector

推荐直接复用仓库里的 `spring-ai-backend/docker-compose.yml` 启动数据库容器。

### 第 1 步：启动数据库

在项目根目录执行：

```bash
cd spring-ai-backend
docker compose up -d
```

容器默认信息：

- MySQL：`127.0.0.1:3306` / 库名 `resume-builder` / 用户 `root` / 密码 `root`
- PostgreSQL + pgvector：`127.0.0.1:5432` / 库名 `resume_builder_vector` / 用户 `postgres` / 密码 `postgres`

### 第 2 步：导入数据库

在 `spring-ai-backend/` 目录执行：

```bash
# AI 面试会话表（必须导入）
docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder < ../sql/interview_schema.sql

# RAG 向量表（使用知识库上传 / 检索时必须导入）
docker exec -i spring-ai-pgvector psql -U postgres -d resume_builder_vector < ../sql/pgvector_rag_schema.sql
```

### 第 3 步：准备 `.env`

将 `python-ai-backend/.env.example` 复制为 `python-ai-backend/.env`，然后至少确认以下配置：

```bash
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173

OPENAI_API_KEY=your_api_key_here
OPENAI_CHAT_MODEL=gpt-5.4
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com
OPENAI_EMBEDDING_API_KEY=your_embedding_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

MYSQL_DATASOURCE_URL=mysql+pymysql://root:root@127.0.0.1:3306/resume-builder
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root

PGVECTOR_DATASOURCE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres
```

### 第 4 步：首次安装依赖

在 `python-ai-backend/` 目录执行：

```bash
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe -r requirements-optional.txt
```

说明：

- `requirements.txt` 是最小可运行依赖。
- `requirements-optional.txt` 推荐一并安装；不安装时，Embedding、RAG、OCR 等能力可能不可用。

### 第 5 步：启动后端

回到项目根目录执行：

```bash
start-python-backend.bat
```

脚本实际行为：

- 创建虚拟环境 `python-ai-backend/.venv`
- 检查核心依赖和可选依赖是否已安装
- 若 `.env` 不存在，则从 `.env.example` 自动复制
- 清理旧的 `8999` 端口监听
- 启动 `uvicorn app.main:app`

注意：`start-python-backend.bat` 不会自动执行 `uv pip install`，首次运行前必须先完成上一步依赖安装。

启动地址：

- `http://127.0.0.1:8999`

健康检查：

- `GET /health`
- `GET /health/runtime`

`/health/runtime` 会返回当前运行进程的 `pid`、工作目录、Python 可执行文件、应用入口文件和启动端口，适合排查是否命中了旧进程。

### 备用方式：PowerShell 启动

在项目根目录执行：

```powershell
.\start-python-backend.ps1 -Port 8999
```

如果需要先停掉旧进程：

```powershell
.\stop-python-backend.ps1 -Port 8999
```

## 与 Spring AI 后端的关系

- `spring-ai-backend` 和 `python-ai-backend` 是同一前端的两套可选后端实现。
- 两者默认都监听 `8999`，前端代理也固定转发到 `8999`。
- 联调时二选一启动即可，不要同时启动两个后端。

## 环境变量配置

环境变量模板文件：

`python-ai-backend/.env.example`

推荐本地联调配置：

```bash
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
APP_RAG_TOP_K=5
APP_INTERVIEW_RAG_TOP_K=5
APP_INTERVIEW_RAG_SIMILARITY_THRESHOLD=0.0
APP_INTERVIEW_RAG_TIMEOUT_SECONDS=3

OPENAI_BASE_URL=https://api.openai.com
OPENAI_API_KEY=your_api_key_here
OPENAI_CHAT_MODEL=gpt-5.4
OPENAI_CHAT_COMPLETIONS_PATH=/v1/chat/completions
OPENAI_CHAT_TIMEOUT_SECONDS=25
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com
OPENAI_EMBEDDING_API_KEY=your_embedding_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_TIMEOUT_SECONDS=45
OLLAMA_EMBEDDING_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_TIMEOUT_SECONDS=45
OPENAI_VISION_MODEL=gpt-4.1
OPENAI_VISION_DETAIL=high

OPENAI_SPEECH_BASE_URL=https://api.openai.com
OPENAI_SPEECH_API_KEY=your_api_key_here
OPENAI_SPEECH_TRANSCRIPTIONS_PATH=/v1/audio/transcriptions
OPENAI_SPEECH_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe

OPENAI_REALTIME_BASE_URL=https://api.openai.com
OPENAI_REALTIME_API_KEY=your_api_key_here
OPENAI_REALTIME_CLIENT_SECRETS_PATH=/v1/realtime/client_secrets
OPENAI_REALTIME_CALLS_PATH=/v1/realtime/calls
OPENAI_REALTIME_TRANSCRIPTION_MODEL=gpt-4o-transcribe
OPENAI_REALTIME_LANGUAGE=zh

MYSQL_DATASOURCE_URL=mysql+pymysql://root:root@127.0.0.1:3306/resume-builder
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root

PGVECTOR_DATASOURCE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres
PGVECTOR_CONNECT_TIMEOUT_SECONDS=8

RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=200
RAG_MAX_FILE_SIZE_MB=10

AUTOGEN_ENABLED=false
```

配置说明：

- `SERVER_PORT`：默认 `8999`，建议保持不变，和前端代理保持一致。
- `APP_CORS_ALLOWED_ORIGINS`：允许访问后端的前端地址，默认 `http://localhost:5173`。
- `start-python-backend.bat` 会检查依赖，但不会自动安装 `requirements.txt`，首次运行前需要先手工执行 `uv pip install`。
- `APP_INTERVIEW_RAG_TOP_K`：AI 面试链路专用检索条数，未配置时兜底 `APP_RAG_TOP_K`。
- `APP_INTERVIEW_RAG_SIMILARITY_THRESHOLD`：AI 面试链路专用相似度阈值（`0-1`），低于阈值的检索片段不会注入模型上下文。
- `APP_INTERVIEW_RAG_TIMEOUT_SECONDS`：AI 面试链路专用检索超时时间（秒），超时后自动跳过 RAG 以保证流式首包尽快返回。
- `OPENAI_*`：聊天、OCR、Embedding、语音、Realtime 等上游模型配置。
- `OPENAI_CHAT_TIMEOUT_SECONDS`：聊天与流式请求超时（秒），用于避免上游模型长时间无响应导致前端一直等待。
- `EMBEDDING_PROVIDER`：Embedding provider 选择，支持 `openai` / `ollama`，默认 `openai`。
- `OPENAI_EMBEDDING_BASE_URL` / `OPENAI_EMBEDDING_API_KEY`：Embedding 可单独走兼容 OpenAI 的第三方路由；未配置时会退回聊天或通用 `OPENAI_*`。
- `OPENAI_EMBEDDING_MODEL`：知识库入库时使用的向量模型，当前示例为 `text-embedding-3-large`；支持 OpenAI 官方模型名，也支持阿里百炼等 OpenAI 兼容网关提供的自定义 embedding model id。
- `OPENAI_EMBEDDING_TIMEOUT_SECONDS`：Embedding 请求超时时间（秒），默认 `45`，避免上传长时间无响应。
- `OLLAMA_EMBEDDING_BASE_URL` / `OLLAMA_EMBEDDING_MODEL` / `OLLAMA_EMBEDDING_TIMEOUT_SECONDS`：当 `EMBEDDING_PROVIDER=ollama` 时生效，分别控制 Ollama 服务地址、模型名和超时配置。
- `OPENAI_VISION_MODEL`：图片 OCR 使用的多模态模型，默认 `gpt-4.1`。
- `OPENAI_VISION_DETAIL`：图片理解 detail 参数，支持 `low/high/original/auto`，默认 `high`。
- 图片 OCR 链路只保留官方 `openai` Python SDK 调用；请求成功时直接返回 OCR 文本，请求失败或返回空内容时直接报错，不再执行额外回退。
- `MYSQL_DATASOURCE_*`：AI 面试会话、历史消息等业务数据存储。
- `PGVECTOR_DATASOURCE_*`：RAG 向量检索存储。`PGVECTOR_DATASOURCE_URL` 可以直接内嵌账号密码，也可以配合 `PGVECTOR_DATASOURCE_USERNAME/PASSWORD` 单独传入。
- `PGVECTOR_CONNECT_TIMEOUT_SECONDS`：连接 pgvector 的超时秒数，默认 `8`，用于快速暴露数据库不可达问题。
- `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP`：知识库内容分块长度与重叠配置。
- FAQ-style knowledge files are first split into blank-line-separated logical documents (`title + answer`), then each logical document is chunked with the configured size and overlap.
- `RAG_MAX_FILE_SIZE_MB`：统一上传接口的单文件大小限制，默认 `10MB`。
- `AUTOGEN_ENABLED`：是否启用 AutoGen 相关能力。

数据库职责划分：

- MySQL：面试会话、对话消息、历史记录。
- PostgreSQL + pgvector：知识库向量存储与相似度检索。

建表脚本：

- `sql/interview_schema.sql`
- 这是仓库内唯一保留的会话建表脚本。
- 需要开发者手工执行一次，应用启动时不会自动建表。
- `sql/pgvector_rag_schema.sql`
- 这是知识库 chunk 与向量表脚本，同样需要开发者手工执行，不会在应用启动时自动执行。

## 目录结构

```text
python-ai-backend/
  app/
    main.py                      # FastAPI 应用入口、CORS、健康检查、路由注册
    api/                         # HTTP 层
      routes/                    # chat / interview / rag / audio / realtime 路由
      schemas/                   # 请求和响应模型
      mappers/                   # API Schema 与 DTO 映射
      deps/                      # 路由依赖提供
      errors/                    # 异常处理
    application/                 # 用例编排层
      use_cases/                 # run_chat / stream_chat / generate_interview_turn 等
      services/                  # chat / interview / rag / audio / realtime 应用服务
      ports/                     # LLM、向量库、会话仓储等抽象端口
      dto/                       # 用例输入输出 DTO
    domain/                      # 领域规则
      chat/                      # 简历优化相关领域逻辑
      interview/                 # 面试流程图与状态流转
      rag/                       # 检索领域服务
      services/                  # 面试流程、RAG、简历段落清洗服务
      policies/                  # 清洗和提示词策略
    infrastructure/              # 外部依赖实现
      config/                    # 配置读取
      db/pgvector/               # 底层 pgvector 向量存储实现
      persistence/mysql/         # MySQL 会话仓储实现
      persistence/pgvector/      # 向量检索适配器
      llm/                       # OpenAI / LangChain / Realtime / Audio 适配
      agents/                    # AutoGen 运行时适配
      factories/                 # 工厂与装配
      text/                      # 技术性文本清洗工具
    bootstrap/                   # 容器与依赖绑定
    shared/                      # SSE / NDJSON / 常量 / 通用类型 / 工具
  .env.example                   # 环境变量模板
  requirements.txt               # 核心依赖
  requirements-optional.txt      # 可选 AI 扩展依赖
  pyproject.toml                 # Python 项目元数据
```

## 功能清单

- `POST /api/ai/chat`
  - 普通问答。
- `POST /api/ai/chat/stream`
  - 流式问答，按 SSE 输出。
- `POST /api/ai/interview/turn/stream`
  - AI 面试流式轮次输出，按 NDJSON 返回。
- `GET /api/ai/interview/sessions`
  - 获取面试历史列表。
- `GET /api/ai/interview/sessions/{session_id}`
  - 获取指定会话详情。
- `POST /api/ai/rag/query`
  - RAG 检索问答。
- `POST /api/ai/rag/documents`
  - RAG 文档入库。
- `POST /api/ai/rag/upload`
  - 统一知识库上传入口，支持 `PDF/TXT/MD/DOCX/PNG/JPG/JPEG/WEBP` 混合上传。
  - 文本文件直接解析内容，图片文件统一通过官方 OpenAI SDK 做 OCR；如果 SDK 失败或返回空内容，则直接返回 OCR 错误。
  - 所有文件统一进入分块、Embedding、pgvector 入库链路，并返回逐文件处理结果。
- `POST /api/ai/audio/transcriptions`
  - 音频转写。
- `POST /api/ai/realtime/client-secret`
  - 生成前端实时语音所需的临时密钥。

## 依赖说明

- `requirements.txt` 为最小可运行依赖，包含 FastAPI、uvicorn、Pydantic、PyMySQL 等。
- `requirements-optional.txt` 为增强能力依赖，用于 LangChain、LangGraph、LlamaIndex、OpenAI SDK、AutoGen、pgvector 等场景。
- 如果可选依赖安装失败，脚本不会阻止核心服务启动，但相关 AI 能力可能不可用。

## PGVector 实际存储说明

- Python 后端当前会真实写入 PostgreSQL 的 `rag_document_chunks` 表，不再使用进程内内存占位存储。
- 写入与检索都通过 pgvector 完成；检索阶段会先对 query 做 Embedding，再按 `embedding_model + embedding_dimensions` 过滤后执行 cosine distance 排序。
- `sql/pgvector_rag_schema.sql` 已调整为不固定维度的 `vector` 列，因此同时兼容 `text-embedding-3-small` 和 `text-embedding-3-large`。
- Python 侧新增了 `psycopg[binary]` 依赖；`PGVECTOR_DATASOURCE_URL` 支持 `jdbc:postgresql://...`、`postgresql://...`、`postgresql+psycopg://...`，启动时会统一归一化为 psycopg 可连接的 URL。
