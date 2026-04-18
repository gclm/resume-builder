<!-- author: jf -->
# python-ai-backend

基于 FastAPI 的 Python AI 后端，实现了与前端现有接口契约兼容的聊天、流式输出、AI 面试、会话存储、RAG、语音转写与 Realtime 临时密钥能力。

## 作用说明

- 对外继续提供 `'/api/ai/*'` 风格接口，前端无需切换请求路径。
- AI 面试会话与消息历史存储到 MySQL。
- RAG 文档向量检索使用 PostgreSQL + pgvector。
- 提供普通问答和流式问答，便于替代或并行参考 Spring AI 后端实现。

## 快速启动

### 推荐方式：项目根目录一键启动

在项目根目录执行：

```bash
start-python-backend.bat
```

脚本会自动完成：

- 检查 `python` 是否已安装并在 `PATH` 中
- 创建虚拟环境 `python-ai-backend/.venv`
- 安装 `requirements.txt`
- 尝试安装 `requirements-optional.txt`
- 若 `.env` 不存在，则从 `.env.example` 自动复制
- 清理旧的 `8999` 端口监听
- 启动 `uvicorn app.main:app`

首次使用前，请先手工执行一次 MySQL 建表脚本：

```bash
mysql -u root -p your_database < sql/interview_schema.sql
```

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

常用配置示例：

```bash
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
APP_RAG_TOP_K=5

OPENAI_BASE_URL=https://api.openai.com
OPENAI_API_KEY=your_api_key_here
OPENAI_CHAT_MODEL=gpt-5.4
OPENAI_CHAT_COMPLETIONS_PATH=/v1/chat/completions

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

AUTOGEN_ENABLED=false
```

配置说明：

- `SERVER_PORT`：默认 `8999`，建议保持不变，和前端代理保持一致。
- `APP_CORS_ALLOWED_ORIGINS`：允许访问后端的前端地址，默认 `http://localhost:5173`。
- `OPENAI_*`：聊天、语音、Realtime 等上游模型配置。
- `MYSQL_DATASOURCE_*`：AI 面试会话、历史消息等业务数据存储。
- `PGVECTOR_DATASOURCE_*`：RAG 向量检索存储。
- `AUTOGEN_ENABLED`：是否启用 AutoGen 相关能力。

数据库职责划分：

- MySQL：面试会话、对话消息、历史记录。
- PostgreSQL + pgvector：知识库向量存储与相似度检索。

建表脚本：

- `sql/interview_schema.sql`
- 这是仓库内唯一保留的会话建表脚本。
- 需要开发者手工执行一次，应用启动时不会自动建表。

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
- `POST /api/ai/audio/transcriptions`
  - 音频转写。
- `POST /api/ai/realtime/client-secret`
  - 生成前端实时语音所需的临时密钥。

## 依赖说明

- `requirements.txt` 为最小可运行依赖，包含 FastAPI、uvicorn、Pydantic、PyMySQL 等。
- `requirements-optional.txt` 为增强能力依赖，用于 LangChain、LangGraph、LlamaIndex、AutoGen、pgvector 等场景。
- 如果可选依赖安装失败，脚本不会阻止核心服务启动，但相关 AI 能力可能不可用。
