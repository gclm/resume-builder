<!-- author: jf -->
# spring-ai-backend

Spring Boot 3 + Spring AI 后端服务，提供聊天、流式输出、语音转写、Realtime 临时密钥、面试会话与 RAG 能力。

该后端与根目录下的 `python-ai-backend` 属于同一前端的两套可选实现，联调时二选一启动即可，不要同时占用 `8999` 端口。

## 技术栈

- Java 21
- Spring Boot 3
- Spring AI
- MyBatis-Plus
- MySQL（业务与面试会话）
- PostgreSQL + pgvector（向量检索）

## 快速开始

在 `spring-ai-backend/` 目录执行：

```bash
# 1) 复制环境变量模板
cp .env.example .env

# 2) 手工执行会话建表脚本
mysql -u root -p your_database < ../sql/interview_schema.sql

# 3) 启动依赖数据库（MySQL + pgvector）
docker compose up -d

# 4) 启动后端
mvn spring-boot:run
```

默认地址：`http://localhost:8999`

健康检查：`GET http://localhost:8999/actuator/health`

## 配置说明

### 1) 必填最小配置（`.env`）

```bash
OPENAI_API_KEY=your_api_key_here
MYSQL_DATASOURCE_URL=jdbc:mysql://localhost:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### 2) pgvector 配置（用于 RAG）

如果使用仓库内 `docker-compose.yml`，请把 `.env` 中 pgvector 相关配置改为：

```bash
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres
```

### 3) 可选分路配置（不同供应商/模型）

- Chat：`OPENAI_CHAT_BASE_URL`、`OPENAI_CHAT_API_KEY`、`OPENAI_CHAT_MODEL`
- Speech：`OPENAI_SPEECH_BASE_URL`、`OPENAI_SPEECH_API_KEY`、`OPENAI_SPEECH_TRANSCRIPTION_MODEL`
- Realtime：`OPENAI_REALTIME_BASE_URL`、`OPENAI_REALTIME_API_KEY`、`OPENAI_REALTIME_TRANSCRIPTION_MODEL`
- Embedding：`OPENAI_EMBEDDING_BASE_URL`、`OPENAI_EMBEDDING_API_KEY`、`OPENAI_EMBEDDING_MODEL`

说明：若保留默认路径（如 `/v1/chat/completions`、`/v1/embeddings`），`*_BASE_URL` 不要再追加 `/v1`。

### 4) `.env` 加载机制

`application.yml` 通过以下配置自动加载同目录 `.env`：

```yaml
spring:
  config:
    import: optional:file:.env[.properties]
```

### 5) 建表脚本

AI 面试会话表与消息表初始化脚本放在项目根目录：

`sql/interview_schema.sql`

说明：

- 该脚本需要开发者手工执行一次。
- 应用启动时不会自动执行建表 SQL。
- Python 后端也复用这份脚本，不再保留第二份会话建表文件。

## 与前端联调

前端（根目录 `vite.config.ts`）已配置代理：

- `'/api' -> 'http://localhost:8999'`
- `'/ws' -> 'http://localhost:8999'`（WebSocket）

前端请求使用相对路径 `'/api'`，无需在前端暴露后端密钥或供应商地址。

## API 摘要

基础路径：`/api/ai`

- `POST /chat`：普通问答
- `POST /chat/stream`：流式问答（SSE）
- `POST /audio/transcriptions`：音频转写
- `POST /realtime/client-secret`：Realtime 临时密钥
- `POST /interview/turn/stream`：面试回合流式输出（NDJSON）
- `GET /interview/sessions?limit=20`：面试会话列表
- `GET /interview/sessions/{sessionId}`：面试会话详情
- `POST /rag/documents`：RAG 文档入库
- `POST /rag/query`：RAG 检索问答

## 常见问题

- 启动后报数据库连接失败：优先检查 `.env` 与 `docker-compose.yml` 的端口、库名、账号是否一致。
- CORS 问题：确认 `APP_CORS_ALLOWED_ORIGINS` 包含前端地址（默认 `http://localhost:5173`）。
- 上游 401/403：确认 `OPENAI_*_API_KEY` 已正确配置且对应供应商可用。
