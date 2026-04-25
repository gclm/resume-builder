<!-- author: jf -->
# spring-ai-backend

Spring Boot 3 + Spring AI 后端服务，提供聊天、流式输出、Realtime 临时密钥、AI 面试会话与 RAG 能力。

## 技术栈

- Java 21
- Spring Boot 3
- Spring AI
- MyBatis-Plus
- MySQL
- PostgreSQL + pgvector

## 快速开始

### 前置依赖

- JDK `21`
- Maven `3.9+`
- Docker Desktop / Docker Compose
- 可用的 OpenAI 或 OpenAI-compatible API Key

### 1. 准备 `.env`

复制 `spring-ai-backend/.env.example` 为 `spring-ai-backend/.env`，至少确认以下配置：

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

### 2. 启动数据库

在 `spring-ai-backend/` 目录执行：

```bash
docker compose up -d
```

### 3. 导入建表脚本

在 `spring-ai-backend/` 目录执行：

```bash
docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder < ../sql/interview_schema.sql
docker exec -i spring-ai-pgvector psql -U postgres -d resume_builder_vector < ../sql/pgvector_rag_schema.sql
```

### 4. 启动后端

在 `spring-ai-backend/` 目录执行：

```bash
mvn spring-boot:run
```

默认地址：`http://localhost:8999`

健康检查：`GET http://localhost:8999/actuator/health`

## 配置说明

### 必填最小配置

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

### 可选分路配置

- Chat：`OPENAI_CHAT_BASE_URL`、`OPENAI_CHAT_API_KEY`、`OPENAI_CHAT_MODEL`
- Realtime：`OPENAI_REALTIME_BASE_URL`、`OPENAI_REALTIME_API_KEY`、`OPENAI_REALTIME_TRANSCRIPTION_MODEL`
- Embedding：`OPENAI_EMBEDDING_BASE_URL`、`OPENAI_EMBEDDING_API_KEY`、`OPENAI_EMBEDDING_MODEL`

说明：

- 保留默认路径时，`*_BASE_URL` 不要再追加 `/v1`。
- `.env` 通过 `spring.config.import=optional:file:.env[.properties]` 自动加载。

## 与前端联调

前端代理默认转发到 `http://localhost:8999`，因此联调时建议保持 `SERVER_PORT=8999`。

## API 摘要

基础路径：`/api/ai`

- `POST /chat`
- `POST /chat/stream`
- `POST /realtime/client-secret`
- `POST /interview/turn/stream`
- `GET /interview/sessions?limit=20`
- `GET /interview/sessions/{sessionId}`
- `POST /rag/documents`
- `POST /rag/query`

## 建表脚本

- `sql/interview_schema.sql`
- `sql/pgvector_rag_schema.sql`

说明：

- 两份脚本都需要开发者手工执行一次。
- 应用启动时不会自动执行建表 SQL。

## 常见问题

- 启动报数据库连接失败时，优先检查 `.env` 与 `docker-compose.yml` 是否一致。
- 遇到 CORS 问题时，确认 `APP_CORS_ALLOWED_ORIGINS` 包含前端地址。
- 上游 401/403 时，确认对应 `OPENAI_*_API_KEY` 已正确配置。
