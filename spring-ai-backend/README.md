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

### 前置依赖

- JDK `21`
- Maven `3.9+`
- Docker Desktop / Docker Compose
- 一个可用的 OpenAI / OpenAI-compatible API Key

### 第 1 步：准备 `.env`

将 `spring-ai-backend/.env.example` 复制为 `spring-ai-backend/.env`，并至少确认以下值：

```bash
OPENAI_API_KEY=your_api_key_here
MYSQL_DATASOURCE_URL=jdbc:mysql://127.0.0.1:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
```

说明：

- `spring-ai-backend/.env.example` 中部分 `PGVECTOR_*` 示例值和当前 `docker-compose.yml` 默认值不一致，复制后请以上面这一组为准。
- 前端开发代理固定转发到 `http://localhost:8999`，所以 `SERVER_PORT` 建议保持 `8999`。

### 第 2 步：启动数据库

在 `spring-ai-backend/` 目录执行：

```bash
docker compose up -d
```

### 第 3 步：导入数据库

在 `spring-ai-backend/` 目录执行：

```bash
# AI 面试会话表（必须导入）
docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder < ../sql/interview_schema.sql

# RAG 向量表（使用知识库上传 / 检索时必须导入）
docker exec -i spring-ai-pgvector psql -U postgres -d resume_builder_vector < ../sql/pgvector_rag_schema.sql
```

### 第 4 步：启动后端

在 `spring-ai-backend/` 目录执行：

```bash
mvn spring-boot:run
```

默认地址：`http://localhost:8999`

健康检查：`GET http://localhost:8999/actuator/health`

## 配置说明

### 1) 必填最小配置（`.env`）

```bash
OPENAI_API_KEY=your_api_key_here
MYSQL_DATASOURCE_URL=jdbc:mysql://127.0.0.1:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### 2) pgvector 配置（用于 RAG）

如果使用当前仓库的 `spring-ai-backend/docker-compose.yml`，请以这组配置为准：

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

数据库初始化脚本放在项目根目录：

- `sql/interview_schema.sql`
- `sql/pgvector_rag_schema.sql`

说明：

- 两份脚本都需要开发者手工执行一次。
- 应用启动时不会自动执行建表 SQL。
- Python 后端也复用这两份脚本。

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
