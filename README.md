<!-- author: jf -->
# Resume Builder

Resume Builder 是一个面向求职场景的简历编辑、模板开发、AI 简历优化、AI 面试与知识库训练一体化项目。前端基于 Vue 3 + Vite，后端提供 Spring AI 与 Python AI Backend 两套实现，二者面向前端保持同一套 `/api/ai/*` 契约，当前核心能力已对齐，联调时二选一启动即可。

## 背景技术介绍

项目目标不是做一个静态简历模板站，而是把“简历内容生产、模板呈现、AI 优化、模拟面试、项目知识沉淀”串成一条可持续迭代的求职准备链路。

核心设计思路：

- 前端负责简历编辑器、模板预览、AI 面板、知识库上传入口和 AI 面试交互。
- Spring AI 后端提供 Java 版本 AI 能力实现，适合 Java / Spring 技术栈联调、工程化验证和 MyBatis + Spring AI 场景。
- Python AI Backend 提供 FastAPI 版本 AI 能力实现，采用 `api -> application -> domain <- infrastructure` 分层，适合快速扩展 AI 编排、RAG 与 Agent 能力。
- MySQL 固定用于 AI 面试会话和消息历史存储。
- PostgreSQL + pgvector 固定用于知识库 RAG 向量存储和相似度检索。
- 前端开发代理固定转发到 `http://localhost:8999`，因此两套后端不要同时启动。

## 功能概览

- 简历编辑：支持基本信息、教育经历、专业技能、工作经历、项目经历、荣誉奖项、个人简介等模块化编辑。
- 模块控制：支持模块显示隐藏、模块顺序调整、自动本地保存和手动保存。
- 模板系统：内置 9 套简历模板，支持新增模板、模板预览、模板切换和 A4 导出。
- 导出导入：支持高清 PDF、压缩 PDF、Markdown、JSON 导出，以及 JSON 回填。
- AI 简历优化：支持按模块流式优化，输出优化建议和优化后内容，并可一键应用与撤销。
- AI 面试：支持候选人模式和面试官模式、开始/暂停/继续/结束评分、会话历史、会话详情、倒计时和流式回答；Spring AI 与 Python AI Backend 均会在面试链路中结合 pgvector 召回项目资料、知识点和题库上下文。
- 知识库：支持文档和图片上传，图片先 OCR 为 Markdown，再进行切块、Embedding 和 pgvector 入库。
- 双后端：Spring AI 与 Python AI Backend 当前对前端 API 保持能力对齐，按团队技术栈二选一联调。

## 页面截图

![模板选择](screenshots/select-template.png)

![简历编辑](screenshots/edit.png)

![AI 优化](screenshots/ai-optimized.png)

![AI 面试](screenshots/ai-interview.png)

## 技术栈

- 前端：Vue 3、TypeScript、Pinia、Vite
- 富文本与渲染：Markdown-It、Vue `v-html` 富文本片段渲染
- 导出：html2pdf.js
- 代码质量：Oxlint、ESLint、vue-tsc、oxfmt
- Java 后端：Java 21、Spring Boot 3、Spring AI、MyBatis-Plus
- Python 后端：Python 3.11+、FastAPI、uv、Uvicorn
- 数据库：MySQL 8.4、PostgreSQL 17 + pgvector
- AI 能力：OpenAI / OpenAI-compatible Chat、Embedding、Vision OCR、Realtime

## 快速开始

### 启动前准备

- Node.js：`^20.19.0 || >=22.12.0`
- Docker Desktop / Docker Compose：用于本地 MySQL + pgvector
- Spring AI 后端：JDK `21`、Maven `3.9+`
- Python AI 后端：Python `3.11+`、`uv`
- OpenAI 或 OpenAI-compatible API Key：用于 Chat、Embedding、OCR、Realtime 等后端能力

### 仅启动前端

适合纯简历编辑、模板开发、导出预览，以及使用 Codex Skill `resume-template-from-image` 按图片生成新模板。

```bash
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

这种模式不需要启动：

- MySQL
- PostgreSQL + pgvector
- `spring-ai-backend`
- `python-ai-backend`

可直接完成：

- 手动编辑简历和切换 9 套内置模板
- 导出高清 PDF、压缩 PDF、Markdown、JSON
- 导入 JSON 回填简历
- 开发或预览新增简历模板
- 使用 `resume-template-from-image` 生成模板后刷新页面查看

### 前后端完整联调

完整联调需要启动前端、数据库，以及一个后端。Spring AI 后端和 Python AI Backend 当前功能对齐，二选一即可，不要同时占用 `8999` 端口。

推荐顺序：

1. 启动 MySQL + pgvector。
2. 手工导入 `sql/` 下的 MySQL 和 pgvector 初始化脚本。
3. 启动前端。
4. 二选一启动 Python AI Backend 或 Spring AI 后端。

### Docker 一键部署

Docker 部署提供三类 profile：

- `spring-ai`：启动前端、Spring AI 后端、MySQL 与 pgvector。
- `python-ai`：启动前端、Python AI Backend、MySQL 与 pgvector。
- `frontend-only`：仅启动前端静态站点，适合模板预览或纯前端功能。

Spring AI 后端套件与 Python 后端套件不能同时启动。两套后端都会在内部网络使用 `backend:8999` 供 Nginx 代理，且都会尝试映射宿主机 `8999`，同时启动会造成端口和代理目标冲突。切换后端前必须先执行：

```bash
docker compose down
```

准备环境变量：

```bash
copy .env.docker.example .env
```

编辑 `.env` 后至少填写真实的 `OPENAI_*_API_KEY`、`DASHSCOPE_API_KEY` 或对应 OpenAI-compatible 上游配置。不要提交包含真实密钥的 `.env` 文件。

Windows 推荐使用项目脚本启动，脚本会自动处理本机已有 MySQL 或 PostgreSQL 的端口占用：

```powershell
.\start-docker-spring-ai.bat
.\start-docker-python-ai.bat
.\stop-docker-stack.bat
```

这两个启动脚本会先执行 `docker compose down`，再启动指定套件；停止脚本只停止当前 stack，不删除 MySQL 和 pgvector 数据卷。

如果宿主机已经有 MySQL 或 PostgreSQL 监听 `.env` 中的 `MYSQL_PORT` / `PGVECTOR_PORT`，启动脚本会跳过对应数据库容器，并把后端连接切到 `host.docker.internal`。如果 `SPRING_PGVECTOR_DATASOURCE_URL` 或 `PYTHON_PGVECTOR_DATASOURCE_URL` 已经指向外部或宿主机 pgvector，启动脚本也会直接跳过 `resume-builder-pgvector` 容器。启动完成后脚本会打印 `docker compose ps` 和当前后端最近日志，并提示你确认宿主机数据库已执行初始化 SQL。

仅启动前端静态站点：

```powershell
docker compose --profile frontend-only up --build -d
```

如果确认宿主机没有占用 `3306` / `5433`，也可以直接使用 Compose 启动完整套件：

```powershell
docker compose --profile spring-ai up --build -d
docker compose --profile python-ai up --build -d
```

如果你希望把 Docker 配置保留在 `.env.docker`，可以先复制配置，再继续使用启动脚本；脚本会在没有 `.env` 时自动读取 `.env.docker`：

```powershell
copy .env.docker.example .env.docker
.\start-docker-spring-ai.bat
.\start-docker-python-ai.bat
```

如果你直接执行 `docker compose --profile spring-ai up --build -d` 或 `docker compose --profile python-ai up --build -d`，Compose 会尝试启动数据库容器；宿主机已有 MySQL 或 PostgreSQL 时可能出现端口占用。此场景必须使用上面的启动脚本。

使用 `start-docker-spring-ai.bat` 或 `start-docker-python-ai.bat` 启动时，脚本会在实际启动 Docker 数据库容器后自动执行初始化 SQL。执行顺序为 MySQL 建库、MySQL 会话表、pgvector 建库、pgvector RAG 表。这个初始化发生在 Docker 启动脚本中，不是 Spring AI 或 Python AI 应用启动自动建表，也不会绕过 `PgVectorStore.initializeSchema(false)` 的约束。

如果脚本检测到宿主机已有 MySQL 或 pgvector 并跳过数据库容器，则不会自动操作宿主机数据库。此时需要你手工执行以下命令。

PowerShell：

```powershell
Get-Content -Raw sql\mysql_database_schema.sql | docker exec -i resume-builder-mysql mysql -uroot -proot
Get-Content -Raw sql\interview_schema.sql | docker exec -i resume-builder-mysql mysql -uroot -proot resume-builder
Get-Content -Raw sql\create_pgvector_resume_builder_database.sql | docker exec -i resume-builder-pgvector psql -v ON_ERROR_STOP=1 -U pgvector -d postgres
Get-Content -Raw sql\pgvector_rag_schema.sql | docker exec -i resume-builder-pgvector psql -U pgvector -d resume-builder
```

cmd / Git Bash：

```bash
docker exec -i resume-builder-mysql mysql -uroot -proot < sql/mysql_database_schema.sql
docker exec -i resume-builder-mysql mysql -uroot -proot resume-builder < sql/interview_schema.sql
docker exec -i resume-builder-pgvector psql -v ON_ERROR_STOP=1 -U pgvector -d postgres < sql/create_pgvector_resume_builder_database.sql
docker exec -i resume-builder-pgvector psql -U pgvector -d resume-builder < sql/pgvector_rag_schema.sql
```

如果 `.env` 中 pgvector 指向本机宿主机，例如 `host.docker.internal:5433/resume-builder`，应使用本机 PostgreSQL 客户端连接 `127.0.0.1:5433` 的 `resume-builder` 数据库后执行 `sql/pgvector_rag_schema.sql`，不要再创建第二套库名或账号。

访问地址：

- 前端：`http://localhost:3000`
- 当前后端健康检查：`http://localhost:8999/health`
- Nginx API 代理：`http://localhost:3000/api/...`
- Nginx WebSocket 代理：`ws://localhost:3000/ws/...`

常见故障：

- 端口占用：检查 `3000`、`8999`、`3306`、`5433` 是否已被其他进程或旧容器占用，必要时先执行 `docker compose down`。
- 数据库未初始化：AI 面试会话表需要 `sql/interview_schema.sql`，RAG 向量表需要 `sql/pgvector_rag_schema.sql`。
- Nginx 502：确认当前只启动了一套后端 profile，并等待后端 `/health` 通过。
- WebSocket 失败：确认使用 Spring AI 后端套件时 `/ws/ai/realtime-asr` 可达，并检查 `DASHSCOPE_API_KEY` 或 Realtime 配置。
- AI Key 缺失：检查 `.env` 或 `.env.docker` 中的 `OPENAI_*_API_KEY`、`DASHSCOPE_API_KEY` 是否仍是占位值。

### 启动数据库

本地数据库容器统一复用 `spring-ai-backend/docker-compose.yml`。

```bash
cd spring-ai-backend
docker compose up -d
```

默认连接信息：

- MySQL：`127.0.0.1:3306`，库名 `resume-builder`，用户 `root`，密码 `root`
- PostgreSQL + pgvector：`127.0.0.1:5433`，库名 `resume-builder`，用户 `pgvector`，密码 `pgvector`

### 导入 MySQL 和 pgvector 数据库文件

数据库初始化脚本统一放在仓库根目录 `sql/`：

- `sql/interview_schema.sql`：MySQL 面试会话表和消息表，Spring / Python 后端共用。
- `sql/pgvector_rag_schema.sql`：PostgreSQL + pgvector 的 `rag_document_chunks` 表，Spring / Python 后端共用。
- `sql/mysql_database_schema.sql`：Docker 初始化 MySQL 数据库时使用，只负责创建 `resume-builder` 数据库。
- `sql/create_pgvector_resume_builder_database.sql`：手工创建 pgvector 数据库时的辅助脚本，Docker Compose 默认已创建 `resume-builder`，通常不需要执行。

在 `spring-ai-backend/` 目录执行以下命令。

PowerShell：

```powershell
Get-Content -Raw ..\sql\mysql_database_schema.sql | docker exec -i spring-ai-mysql mysql -uroot -proot
Get-Content -Raw ..\sql\interview_schema.sql | docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder
Get-Content -Raw ..\sql\create_pgvector_resume_builder_database.sql | docker exec -i spring-ai-pgvector psql -v ON_ERROR_STOP=1 -U pgvector -d postgres
Get-Content -Raw ..\sql\pgvector_rag_schema.sql | docker exec -i spring-ai-pgvector psql -U pgvector -d resume-builder
```

cmd / Git Bash：

```bash
docker exec -i spring-ai-mysql mysql -uroot -proot < ../sql/mysql_database_schema.sql
docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder < ../sql/interview_schema.sql
docker exec -i spring-ai-pgvector psql -v ON_ERROR_STOP=1 -U pgvector -d postgres < ../sql/create_pgvector_resume_builder_database.sql
docker exec -i spring-ai-pgvector psql -U pgvector -d resume-builder < ../sql/pgvector_rag_schema.sql
```

注意：

- MySQL 面试会话表和 pgvector RAG 向量表都不会在应用启动时自动建表。
- Spring AI 后端必须保持 `PgVectorStore.initializeSchema(false)`，只读写已手工创建的 `rag_document_chunks`。
- PostgreSQL + pgvector 只用于 RAG，不用于会话表存储。

### 启动前端

回到仓库根目录：

```bash
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

Vite 代理配置：

- `/api` -> `http://localhost:8999`
- `/ws` -> `http://localhost:8999`

### 启动 Python AI 后端

Python 后端推荐用仓库根目录的 `start-python-backend.bat` 启动。该脚本会复用或创建 `python-ai-backend/.venv`、检查依赖、缺少 `.env` 时从 `.env.example` 复制、清理旧的 `8999` 监听并启动 Uvicorn。

首次运行前需要手工安装依赖，`start-python-backend.bat` 不会自动安装 `requirements.txt`：

```bash
cd python-ai-backend
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe -r requirements-optional.txt
cd ..
```

准备 `.env`：

```bash
copy python-ai-backend\.env.example python-ai-backend\.env
```

启动：

```bash
start-python-backend.bat
```

备用 PowerShell 方式：

```powershell
.\start-python-backend.ps1 -Port 8999
```

健康检查：

- `http://127.0.0.1:8999/health`
- `http://127.0.0.1:8999/health/runtime`

更多说明见 [python-ai-backend/README.md](python-ai-backend/README.md)。

### Spring AI 后端启动说明

准备 `.env`：

```bash
copy spring-ai-backend\.env.example spring-ai-backend\.env
```

启动：

```bash
cd spring-ai-backend
mvn spring-boot:run
```

默认地址：`http://localhost:8999`

健康检查：

- `http://localhost:8999/actuator/health`

更多说明见 [spring-ai-backend/README.md](spring-ai-backend/README.md)。

## `.env` 配置说明

两套后端都使用各自目录下的 `.env.example` 作为模板：

- Spring AI：`spring-ai-backend/.env.example`
- Python AI Backend：`python-ai-backend/.env.example`

### 公共最小配置

```dotenv
# 后端端口，必须与 Vite 代理目标保持一致。
SERVER_PORT=8999

# 前端开发地址，用于 CORS 放行。
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173

# RAG 默认召回数量。
APP_RAG_TOP_K=5

# AI 面试中用于知识库增强的召回数量。
APP_INTERVIEW_RAG_TOP_K=4

# AI 面试 RAG 命中阈值，越高越严格。
APP_INTERVIEW_RAG_SIMILARITY_THRESHOLD=0.5

# AI 面试 RAG 检索超时时间，避免面试流式输出被长时间阻塞。
APP_INTERVIEW_RAG_TIMEOUT_SECONDS=3
```

### OpenAI / Chat 配置

```dotenv
# OpenAI 或 OpenAI-compatible 服务根地址。
OPENAI_BASE_URL=https://api.openai.com

# 通用 API Key；不拆分供应商时可作为 Chat / Embedding / OCR / Realtime 的默认 Key。
OPENAI_API_KEY=your_api_key_here

# Chat 专用服务地址；不配置时通常回退到 OPENAI_BASE_URL。
OPENAI_CHAT_BASE_URL=https://api.openai.com

# Chat 专用 API Key；不配置时通常回退到 OPENAI_API_KEY。
OPENAI_CHAT_API_KEY=your_chat_api_key_here

# Chat Completions 路径，兼容 OpenAI-compatible 上游。
OPENAI_CHAT_COMPLETIONS_PATH=/v1/chat/completions

# 聊天与简历优化使用的模型。
OPENAI_CHAT_MODEL=gpt-5.4

# Chat 请求超时时间。
OPENAI_CHAT_TIMEOUT_SECONDS=25
```

### Embedding 配置

```dotenv
# openai 使用 OPENAI_EMBEDDING_*，ollama 使用本地 OLLAMA_EMBEDDING_*。
EMBEDDING_PROVIDER=openai

# Spring AI 使用；0 表示按常见模型自动推断，自定义 Ollama 模型建议显式填写真实维度。
EMBEDDING_DIMENSIONS=0

# OpenAI Embedding 服务地址。
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com

# OpenAI Embedding API Key。
OPENAI_EMBEDDING_API_KEY=your_embedding_api_key_here

# OpenAI Embeddings 路径，Spring AI 后端使用。
OPENAI_EMBEDDINGS_PATH=/v1/embeddings

# 知识库向量化模型。
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Embedding 请求超时时间。
OPENAI_EMBEDDING_TIMEOUT_SECONDS=20

# Ollama 本地 Embedding 服务地址。
OLLAMA_EMBEDDING_BASE_URL=http://127.0.0.1:11434

# Ollama Embedding 模型；使用前先执行 ollama pull nomic-embed-text。
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Ollama Embedding 请求超时时间。
OLLAMA_EMBEDDING_TIMEOUT_SECONDS=45
```

### Vision OCR 配置

```dotenv
# 图片 OCR 使用的视觉模型服务地址。
OPENAI_VISION_BASE_URL=https://api.openai.com

# 图片 OCR 专用 API Key；不拆分时可复用 OPENAI_API_KEY。
OPENAI_VISION_API_KEY=your_vision_api_key_here

# Spring AI 后端视觉模型 Chat Completions 路径。
OPENAI_VISION_CHAT_COMPLETIONS_PATH=/v1/chat/completions

# 图片 OCR 使用的视觉模型。
OPENAI_VISION_MODEL=gpt-4.1

# 图片 OCR 请求超时时间。
OPENAI_VISION_TIMEOUT_SECONDS=40

# 图片细节等级，通常使用 high 提高 OCR 质量。
OPENAI_VISION_DETAIL=high
```

### Realtime 语音配置

Python 后端使用 OpenAI Realtime WebRTC client-secret 链路。OpenAI 官方文档也建议浏览器或移动端连接 Realtime 模型时优先使用 WebRTC，并由服务端签发临时凭据，标准 API Key 只放在后端。

```dotenv
# OpenAI Realtime 服务地址。
OPENAI_REALTIME_BASE_URL=https://api.openai.com

# Realtime 专用 API Key；不拆分时可复用 OPENAI_API_KEY。
OPENAI_REALTIME_API_KEY=your_realtime_api_key_here

# 创建浏览器临时凭据的接口路径。
OPENAI_REALTIME_CLIENT_SECRETS_PATH=/v1/realtime/client_secrets

# WebRTC SDP 建连接口路径。
OPENAI_REALTIME_CALLS_PATH=/v1/realtime/calls

# 实时转写模型。
OPENAI_REALTIME_TRANSCRIPTION_MODEL=gpt-4o-transcribe

# 实时语音语言。
OPENAI_REALTIME_LANGUAGE=zh

# Spring AI 后端 OpenAI provider 创建临时凭据时的请求超时时间。
OPENAI_REALTIME_TIMEOUT_SECONDS=120
```

Spring AI 后端默认实时语音链路是 `dashscope`，前端连接 Spring WebSocket，Spring 再桥接 DashScope realtime ASR：

```dotenv
# dashscope：前端连 Spring /ws/ai/realtime-asr；openai：前端走 OpenAI Realtime WebRTC。
REALTIME_ASR_PROVIDER=dashscope

# DashScope API Key。
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# DashScope realtime ASR WebSocket 地址。
DASHSCOPE_REALTIME_BASE_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime

# DashScope realtime ASR 模型。
DASHSCOPE_REALTIME_MODEL=qwen3-asr-flash-realtime

# 识别语言。
DASHSCOPE_REALTIME_LANGUAGE=zh

# PCM 采样率。
DASHSCOPE_REALTIME_SAMPLE_RATE=16000

# VAD 阈值。
DASHSCOPE_REALTIME_VAD_THRESHOLD=0.2

# VAD 静音结束时长。
DASHSCOPE_REALTIME_VAD_SILENCE_DURATION_MS=800

# DashScope WebSocket 建连超时时间。
DASHSCOPE_REALTIME_OPEN_TIMEOUT_SECONDS=10
```

### MySQL 配置

Spring AI：

```dotenv
# MySQL JDBC URL，固定用于 AI 面试会话与消息历史。
MYSQL_DATASOURCE_URL=jdbc:mysql://127.0.0.1:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true

# MySQL 用户名。
MYSQL_DATASOURCE_USERNAME=root

# MySQL 密码。
MYSQL_DATASOURCE_PASSWORD=root
```

Python AI Backend：

```dotenv
# SQLAlchemy MySQL URL，固定用于 AI 面试会话与消息历史。
MYSQL_DATASOURCE_URL=mysql+pymysql://root:root@127.0.0.1:3306/resume-builder

# MySQL 用户名。
MYSQL_DATASOURCE_USERNAME=root

# MySQL 密码。
MYSQL_DATASOURCE_PASSWORD=root
```

### PostgreSQL + pgvector 配置

Spring AI：

```dotenv
# PostgreSQL JDBC URL，固定用于 RAG 向量库。
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5433/resume-builder

# PostgreSQL 用户名。
PGVECTOR_DATASOURCE_USERNAME=pgvector

# PostgreSQL 密码。
PGVECTOR_DATASOURCE_PASSWORD=pgvector

# PostgreSQL JDBC Driver。
PGVECTOR_DATASOURCE_DRIVER_CLASS_NAME=org.postgresql.Driver

# pgvector 连接超时时间。
PGVECTOR_CONNECT_TIMEOUT_SECONDS=8
```

Python AI Backend：

```dotenv
# SQLAlchemy PostgreSQL URL，固定用于 RAG 向量库。
PGVECTOR_DATASOURCE_URL=postgresql+psycopg://pgvector:pgvector@127.0.0.1:5433/resume-builder

# PostgreSQL 用户名。
PGVECTOR_DATASOURCE_USERNAME=pgvector

# PostgreSQL 密码。
PGVECTOR_DATASOURCE_PASSWORD=pgvector

# pgvector 连接超时时间。
PGVECTOR_CONNECT_TIMEOUT_SECONDS=8
```

### RAG 文档处理配置

```dotenv
# 单个文本块最大长度。
RAG_CHUNK_SIZE=700

# 相邻文本块重叠长度。
RAG_CHUNK_OVERLAP=70

# 知识库单文件上传大小限制。
RAG_MAX_FILE_SIZE_MB=10
```

### AutoGen 配置

```dotenv
# 是否启用 AutoGen / 多 Agent 扩展能力，默认关闭。
AUTOGEN_ENABLED=false
```

## 知识库使用说明

知识库入口位于前端左侧菜单。它用于把项目背景、技术细节、量化结果、面试题库、追问链路等资料沉淀到 pgvector 中，供 RAG 问答和 AI 面试召回复用。

当前支持文件类型：

- 文档：`PDF / TXT / MD / DOCX`
- 图片：`PNG / JPG / JPEG / WEBP`
- 默认单文件大小限制：`10MB`

处理链路：

1. 上传文件到 `POST /api/ai/rag/upload`。
2. 普通文档直接解析为文本。
3. 图片先通过 Vision OCR 转为 Markdown。
4. 文本按标题、段落、问题边界进行切块。
5. 使用配置的 Embedding provider 生成向量。
6. 写入 PostgreSQL + pgvector 的 `rag_document_chunks`。
7. AI 面试或 RAG 问答时按问题召回相关片段并注入上下文。

推荐知识库文档写法：

```md
## 项目背景

这里写项目面向的人群、业务目标、核心痛点和收益。

## 技术方案

这里写架构分层、数据库选择、缓存策略、RAG 链路和关键取舍。

Q1: 为什么会话存 MySQL，而知识库存 pgvector？

MySQL 适合稳定保存结构化会话数据，pgvector 适合对知识片段做向量相似度检索。

Q2: AI 面试为什么要接知识库？

面试问题可以先命中项目资料、技术方案和题库答案，再生成更贴近真实项目的追问和反馈。
```

使用建议：

- 项目经历、技术方案、量化结果优先用 `.md` 或 `.txt`。
- 一份文档只写一个主题，减少噪声召回。
- 标题使用 `##`、`###`，问题使用 `Q1:`、`Q2:`，有利于切块。
- 不要把真实密钥、公司敏感数据、不可公开材料上传到本地以外的上游模型服务。

## 常用脚本

```bash
# 前端开发
npm run dev

# 构建，包含类型检查
npm run build

# 仅构建前端产物
npm run build-only

# 预览构建结果
npm run preview

# 类型检查
npm run type-check

# 代码检查并自动修复
npm run lint

# 格式化 src 目录
npm run format

# 启动 Python AI Backend
start-python-backend.bat

# PowerShell 启动 Python AI Backend
.\start-python-backend.ps1 -Port 8999

# 停止占用 8999 的 Python 后端进程
.\stop-python-backend.ps1 -Port 8999

# Docker 一键启动 Spring AI 套件
.\start-docker-spring-ai.bat

# Docker 一键启动 Python AI 套件
.\start-docker-python-ai.bat

# 停止 Docker stack，不删除数据卷
.\stop-docker-stack.bat

# Docker Compose 直接启动 Spring AI 套件（仅适合 3306/5433 未被宿主机占用）
docker compose --profile spring-ai up --build -d

# Docker Compose 直接启动 Python AI 套件（仅适合 3306/5433 未被宿主机占用）
docker compose --profile python-ai up --build -d

# 启动 Spring AI 后端
cd spring-ai-backend
mvn spring-boot:run

# 仅容器部署前端静态站点
docker compose --profile frontend-only up --build -d
```

## 目录结构

```text
resume-builder/
  src/
    api/                         # 前端请求定义，统一从 /api 走 Vite 代理
    assets/templates/resume/     # 简历模板预览图
    components/
      ai/                        # AI 配置、AI 优化、AI 面试、知识库界面
      common/                    # 通用组件
      resume/                    # 简历编辑器与预览组件
    services/                    # 前端业务编排、AI 调用、Realtime 服务
    stores/                      # Pinia 状态，包含简历数据和 AI 配置
    templates/resume/            # 简历模板实现与注册入口
  python-ai-backend/
    app/
      api/                       # FastAPI 路由、Schema、Mapper、错误处理
      application/               # Use Case、应用服务、端口、DTO
      domain/                    # Chat / Interview / RAG 领域规则
      infrastructure/            # 配置、MySQL、pgvector、LLM、Agent 适配
      bootstrap/                 # 依赖装配
      shared/                    # SSE / NDJSON / 通用工具
    .env.example                 # Python 后端环境变量模板
    requirements.txt             # Python 核心依赖
    requirements-optional.txt    # Python 可选 AI 依赖
  spring-ai-backend/
    src/main/java/com/resumebuilder/springaibackend/
      controller/                # /api/ai/* 接口
      service/                   # 业务编排 Service
      mapper/                    # MyBatis Mapper 接口
      entity/                    # 持久化实体与查询行对象
      dto/                       # API 请求、响应、流式事件 DTO
      client/                    # OpenAI / DashScope 等上游 client
      vector/                    # pgvector / VectorStore 适配
      embedding/                 # Embedding provider
      ocr/                       # 图片 OCR 支撑
      realtime/                  # Realtime WebSocket 与协议桥接
      parser/                    # 文档解析
      chunking/                  # 文本切块
      config/                    # 配置与 Bean 装配
      exception/                 # 异常处理
    src/main/resources/mapper/   # MyBatis XML SQL
    .env.example                 # Spring AI 后端环境变量模板
    docker-compose.yml           # MySQL + pgvector 本地容器
  sql/
    interview_schema.sql         # MySQL 面试会话初始化脚本
    pgvector_rag_schema.sql      # pgvector RAG 向量表初始化脚本
    create_pgvector_resume_builder_database.sql
  screenshots/                   # README 页面截图
  docs/
    harness-engineering-workflow.md
    requirements/                # 历史任务需求文档
  .codex/skills/                 # 项目内置 Codex Skills
  start-python-backend.bat       # Python 后端一键启动脚本
  start-python-backend.ps1       # Python 后端 PowerShell 启动脚本
  stop-python-backend.ps1        # Python 后端端口清理脚本
```

## 后端 API 摘要

两套后端对前端保持同一套基础契约，基础路径为 `/api/ai`：

- `POST /chat`：普通问答
- `POST /chat/stream`：SSE 流式问答
- `POST /realtime/client-secret`：Realtime 会话配置接口
- `WS /ws/ai/realtime-asr`：Spring AI 后端 DashScope realtime ASR 桥接通道
- `POST /interview/turn/stream`：AI 面试流式回合，NDJSON
- `GET /interview/sessions`：面试会话列表
- `GET /interview/sessions/{sessionId}`：面试会话详情
- `POST /rag/query`：RAG 检索问答
- `POST /rag/documents`：RAG 文档入库
- `POST /rag/upload`：知识库统一上传入口

## 内置 Codex Skills

项目内置技能目录：`.codex/skills/`

与本项目强相关的 Skills：

- `resume-template-from-image`：根据用户上传的简历模板图片，直接生成项目可用的新模板。
- `resume-backend-project-optimizer`：把中文后端项目经历改写为更适合 Java 后端求职的简历要点。
- `resume-interview-coach`：围绕项目经历进行面试追问、STAR 话术构建和简历防御。
- `code-review`：按项目规则输出中文代码审查报告和评分。
- `code-review-fix`：读取审查报告并修复 P0/P1 或必要问题。
- `pr-review-fix`：读取 PR 审查结果并修复中高风险问题。

### `resume-template-from-image` 重点说明

用途：用户给一张简历模板图片，Codex 按当前项目模板规范生成一套可切换的新模板，包含 Vue 组件、模板注册和模板预览图。

适合场景：

- 想把一张简历截图变成当前项目内置模板。
- 想快速扩展模板库，但不想手工写完整 Vue 模板。
- 只做模板开发，不需要启动后端或数据库。

使用前只需要启动前端：

```bash
npm run dev
```

生成内容固定接入：

- `src/templates/resume/<key>/ResumeTemplate.vue`
- `src/templates/resume/<key>/template.ts`
- `src/assets/templates/resume/<key>-preview.svg`
- `src/templates/resume/index.ts`

使用提示词示例：

```text
请使用 resume-template-from-image，根据我上传的图片生成一个新的简历模板。
模板名称：深蓝商务模板
模板 key：deep-blue-business
要求：保持 A4 预览兼容，接入当前模板注册体系，预览图使用骨架 SVG。
```

关键规则：

- 必须复用 `useResumeTemplateData()` 和现有 `resume` store 字段。
- 不允许新增简历数据模型字段。
- 模块标题必须与编辑区一致，如 `教育经历`、`专业技能`、`工作经历`、`项目经历`、`荣誉奖项`、`个人简介`。
- 模块顺序必须跟随编辑区顺序，`basicInfo` 固定首位。
- 预览图必须是 `800 x 1120` 风格的骨架 SVG，不允许空白占位，不允许直接复用旧模板预览图。

## Harness Workflow

仓库级 Harness Engineering 工作流见 [docs/harness-engineering-workflow.md](docs/harness-engineering-workflow.md)。

当前仓库协作入口：

- `AGENTS.md`：仓库级 AI 执行规范。
- `.rules/`：前端、后端、Spring AI、Python AI、MCP、审查等强制规则。
- `docs/requirements/`：多步骤任务的需求文档与验收记录。
- `README.md`：产品能力、启动方式、环境变量、知识库和协作入口总览。

执行原则：

- 新增功能或行为变更先拆任务，再定义验收，再实现。
- 前端页面和交互变化优先用 Playwright 验证。
- OpenAI 能力、模型、API 迁移优先查询官方 OpenAI docs MCP。
- PR、Issue、Review、Checks 相关任务优先读取 GitHub 上下文。
- 长期有效知识写回仓库文档，不只留在对话或 memory。

## 友情链接

- [Linux.do](https://linux.do/)
- [OpenAI Harness Engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/)
- [OpenAI API Docs](https://developers.openai.com/api/docs/)
- [Vue](https://vuejs.org/)
- [Vite](https://vite.dev/)
- [Spring AI](https://spring.io/projects/spring-ai)
- [FastAPI](https://fastapi.tiangolo.com/)
- [pgvector](https://github.com/pgvector/pgvector)

## License

MIT
