<!-- author: jf -->
# Resume Builder

一个基于 Vue 3 + Vite 的简历编辑与 AI 面试一体化项目，当前同时支持 `spring-ai-backend` 和 `python-ai-backend` 两套后端实现，覆盖简历优化、AI 面试、知识库入库与检索、流式回复、语音输入与会话存储。

## 功能概览

### 1) 简历编辑
- 模块化编辑：基本信息、教育经历、专业技能、工作经历、项目经历、荣誉奖项、个人简介
- 模块可见性开关与顺序调整（`basicInfo` 固定首位）
- 自动本地保存与手动保存草稿
- 模板切换（当前内置 9 套模板：默认模板、蓝色线性模板、绿色图标线性模板、黑白线性模板、通用职场模板、蓝色侧栏职场模板、蓝色分栏专业模板、蓝色卡片模板、红色渐变模板）
- 导出能力：高清 PDF、压缩 PDF、Markdown、JSON
- 支持导出 JSON 简历进度，并通过导入 JSON 一键回填当前简历内容

### 2) AI 优化（简历模块）
- 通过后端接口进行流式优化（SSE）
- 支持分模块优化并输出“优化建议 + 优化后内容”
- 一键应用优化结果并支持撤销
- 当前可直接应用模块：`skills`、`selfIntro`、`workExperience`、`projectExperience`、`awards`

### 3) AI 面试
- 双模式切换：
  - 候选人模式（AI 扮演面试官）
  - 面试官模式（AI 扮演候选人）
- 面试控制：开始、暂停/继续、结束并评分、重置、时长 `-5m/+5m`
- 倒计时范围：15~120 分钟，超时可自动触发结束评分
- 历史会话列表与会话详情恢复
- 流式回复渲染（NDJSON）
- 语音输入：
  - 优先使用后端实时语音
  - 不可用时自动降级到浏览器语音识别
  - 快捷键 `Ctrl + I` 开关语音
- 已结束会话不可继续/发送消息
- 在 `python-ai-backend` 下，AI 面试链路会先从 pgvector 检索项目资料、知识点和面试题上下文，再把命中内容注入本轮问答，提升回答真实性，减少内容过宽泛、脱离简历或发生漂移

### 4) 知识库
- 左侧菜单内置独立“知识库”入口，支持统一上传文档与图片
- 当前支持文件类型：`PDF / TXT / MD / DOCX / PNG / JPG / JPEG / WEBP`
- 图片文件会先做 OCR 转 Markdown，再进入分块、Embedding 和 pgvector 入库链路
- 可沉淀项目背景、技术细节、量化结果、项目问答、常见八股题，供 AI 面试和 RAG 检索复用

## 页面截图

![模板选择](screenshots/select-template.png)
![简历编辑](screenshots/edit.png)
![AI 优化](screenshots/ai-optimized.png)
![AI 面试](screenshots/ai-interview.png)

## 技术栈

- 前端：Vue 3、TypeScript、Pinia、Vite
- 富文本/渲染：Markdown-It
- 导出：html2pdf.js
- 代码质量：Oxlint、ESLint、vue-tsc
- 后端：Spring Boot 3 + Spring AI，FastAPI + Python AI Backend
- 数据库：MySQL（业务/面试会话）、PostgreSQL + pgvector（RAG 向量检索）

## 快速开始

### 启动前准备

- 前端：Node.js `^20.19.0 || >=22.12.0`
- Spring AI 后端：JDK `21`、Maven `3.9+`
- Python AI 后端：Python `3.11+`、`uv`
- 数据库：推荐直接复用 `spring-ai-backend/docker-compose.yml` 启动 MySQL + pgvector

如果你只是做简历编辑、切换模板、导出或导入 JSON，或者只想调用 Codex 的 `resume-template-from-image` 按图片生成新模板，不需要启动后端，也不需要启动 MySQL / PostgreSQL + pgvector。

### 方式 A：仅启动前端（适合纯简历编辑 / 模板开发 / `resume-template-from-image`）

```bash
npm install
npm run dev
```

默认地址：`http://localhost:5173`

这种模式下可直接完成：

- 手动编辑简历、切换 9 套内置模板
- 导出高清 PDF、压缩 PDF、Markdown、JSON
- 导入 JSON 一键回填简历
- 预览由 `resume-template-from-image` 生成的新模板

这种模式下不需要启动：

- MySQL
- PostgreSQL + pgvector
- `spring-ai-backend`
- `python-ai-backend`

### 方式 B：前后端联调（推荐，后端二选一，优先 Python AI Backend）

前端开发代理固定转发到 `http://localhost:8999`，所以联调时只需要在 `spring-ai-backend` 和 `python-ai-backend` 中二选一启动即可，不要同时启动两个后端。

只要你要使用以下任意能力，就需要先准备数据库并启动一个后端：

- AI 优化
- AI 面试
- 知识库上传 / OCR / 向量检索
- Realtime 语音、音频转写

当前更推荐优先启动 `python-ai-backend`，因为知识库统一上传、图片 OCR 入库，以及 AI 面试结合向量库检索项目资料/面试题上下文的链路说明更完整。

#### 第 1 步：启动数据库容器（MySQL + pgvector）

数据库容器统一放在 `spring-ai-backend/docker-compose.yml`，两套 AI 后端都可以复用：

```bash
cd spring-ai-backend
docker compose up -d
```

容器默认信息：

- MySQL：`127.0.0.1:3306` / 库名 `resume-builder` / 用户 `root` / 密码 `root`
- PostgreSQL + pgvector：`127.0.0.1:5432` / 库名 `resume_builder_vector` / 用户 `postgres` / 密码 `postgres`

#### 第 2 步：导入数据库

本仓库不会在应用启动时自动建表，首次联调前需要手工导入 SQL。

在 `spring-ai-backend/` 目录执行：

```bash
# AI 面试会话表（Spring / Python 共用，必须导入）
docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder < ../sql/interview_schema.sql

# RAG 向量表（使用知识库上传 / 检索时必须导入）
docker exec -i spring-ai-pgvector psql -U postgres -d resume_builder_vector < ../sql/pgvector_rag_schema.sql
```

说明：

- `sql/interview_schema.sql`：MySQL 会话表，AI 面试功能必须依赖它。
- `sql/pgvector_rag_schema.sql`：PostgreSQL + pgvector 表结构，知识库上传、OCR 入库、RAG 检索、AI 面试检索增强都需要它。
- 两份 SQL 都需要开发者手工执行一次，任意后端启动时都不会自动建表。

#### 第 3 步：启动前端（项目根目录）

```bash
npm install
npm run dev
```

前端地址：`http://localhost:5173`

#### 第 4 步：二选一启动一个 AI 后端（不要同时启动）

#### 方案 B1：启动 Spring AI 后端

1. 将 `spring-ai-backend/.env.example` 复制为 `spring-ai-backend/.env`。
2. 建议至少显式配置以下最小必填项；如果你不拆分不同供应商的 Key，`OPENAI_API_KEY` 一项即可作为 Chat / Speech / Realtime / Embedding 的默认 Key：

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

3. 在 `spring-ai-backend/` 目录启动后端：

```bash
mvn spring-boot:run
```

启动后访问：

- `http://127.0.0.1:8999/actuator/health`

更多说明见 [spring-ai-backend/README.md](spring-ai-backend/README.md)。

#### 方案 B2：启动 Python AI 后端（推荐）

1. 将 `python-ai-backend/.env.example` 复制为 `python-ai-backend/.env`。
2. 推荐至少显式配置以下最小可用项；其中 `OPENAI_API_KEY` 可作为 Chat / Embedding / OCR / Speech / Realtime 的统一默认 Key，专用 `OPENAI_*_API_KEY` 不配时会自动回退：

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
PGVECTOR_DATASOURCE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resume_builder_vector
AUTOGEN_ENABLED=false
```

3. 首次运行前，在 `python-ai-backend/` 目录安装依赖：

```bash
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe -r requirements-optional.txt
```

4. 回到项目根目录执行：

```bash
start-python-backend.bat
```

这个脚本当前会自动完成以下动作：

- 创建 `python-ai-backend/.venv`
- 检查核心依赖和可选 AI 依赖是否已安装
- 若缺少 `.env`，自动从 `python-ai-backend/.env.example` 复制生成
- 先清理旧的 `8999` 端口监听，再启动 `uvicorn`

注意：`start-python-backend.bat` 不会自动执行 `uv pip install`，首次运行必须先手工安装依赖。

启动后可访问：

- 健康检查：`http://127.0.0.1:8999/health`
- 运行时检查：`http://127.0.0.1:8999/health/runtime`

更多说明见 [python-ai-backend/README.md](python-ai-backend/README.md)。

### 方式 C：仅容器部署前端静态站点

```bash
docker compose up --build -d
```

访问：`http://localhost:3000`

## 环境配置

### 前端（Vite 代理）

- 前端接口统一使用相对路径 `'/api'`，常量定义在 `src/api/apiBase.ts`。
- 开发环境代理定义在 `vite.config.ts`：
  - `'/api' -> 'http://localhost:8999'`
  - `'/ws' -> 'http://localhost:8999'`（`ws: true`）
- 当前前端已不再使用 `VITE_AI_BACKEND_URL`。
- 当前推荐保持后端端口为 `8999`，切换后端实现时无需改前端代理。
- `spring-ai-backend` 和 `python-ai-backend` 共享这一代理端口，所以同一时间只能启动一个后端。

### 后端环境变量

只要你准备启动任意后端，建议优先把以下公共最小项配好：

- `SERVER_PORT=8999`
- `APP_CORS_ALLOWED_ORIGINS=http://localhost:5173`
- `OPENAI_API_KEY=...`
- `MYSQL_DATASOURCE_URL=...`
- `PGVECTOR_DATASOURCE_URL=...`

其中：

- MySQL 固定用于 AI 面试会话和历史消息存储
- PostgreSQL + pgvector 固定用于知识库向量检索，不用于会话表
- `sql/interview_schema.sql` 和 `sql/pgvector_rag_schema.sql` 都需要开发者手工导入一次

#### Spring AI 后端

模板文件：`spring-ai-backend/.env.example`

推荐本地联调配置（`.env`）：

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

- `spring-ai-backend/.env.example` 中部分 `PGVECTOR_*` 示例值不是当前 `docker compose` 默认值，复制后请以上面这一组为准。
- `application.yml` 已通过 `spring.config.import=optional:file:.env[.properties]` 自动加载 `.env`，无需把密钥写入源码。
- 从 Spring Boot 配置回退逻辑看，最小必填可收敛为：`OPENAI_API_KEY`、`MYSQL_DATASOURCE_URL`、`PGVECTOR_DATASOURCE_URL`；但本仓库仍然强烈建议把用户名、密码、端口和 CORS 一并显式写入 `.env`，避免环境差异。

可选分路配置（不同模型/供应商）：

- Chat：`OPENAI_CHAT_BASE_URL`、`OPENAI_CHAT_API_KEY`、`OPENAI_CHAT_MODEL`
- Speech：`OPENAI_SPEECH_BASE_URL`、`OPENAI_SPEECH_API_KEY`
- Realtime：`OPENAI_REALTIME_BASE_URL`、`OPENAI_REALTIME_API_KEY`
- Embedding：`OPENAI_EMBEDDING_BASE_URL`、`OPENAI_EMBEDDING_API_KEY`、`OPENAI_EMBEDDING_MODEL`、`OPENAI_EMBEDDING_TIMEOUT_SECONDS`

建议理解为：

- 只想快速跑通：先配 `OPENAI_API_KEY + MySQL + pgvector + 端口/CORS`
- 需要分供应商或分模型：再补对应的 `OPENAI_CHAT_*`、`OPENAI_SPEECH_*`、`OPENAI_REALTIME_*`、`OPENAI_EMBEDDING_*`

#### Python AI 后端

模板文件：`python-ai-backend/.env.example`

推荐本地联调配置（`.env`）：

```bash
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
APP_RAG_TOP_K=5

OPENAI_BASE_URL=https://api.openai.com
OPENAI_API_KEY=your_api_key_here
OPENAI_CHAT_MODEL=gpt-5.4
OPENAI_CHAT_COMPLETIONS_PATH=/v1/chat/completions
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com
OPENAI_EMBEDDING_API_KEY=your_embedding_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_TIMEOUT_SECONDS=45
OLLAMA_EMBEDDING_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_TIMEOUT_SECONDS=45

MYSQL_DATASOURCE_URL=mysql+pymysql://root:root@127.0.0.1:3306/resume-builder
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root

PGVECTOR_DATASOURCE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres

AUTOGEN_ENABLED=false
```

说明：

- MySQL 只负责 AI 面试会话与消息历史存储。
- PostgreSQL + pgvector 只负责 RAG 向量检索，不用于会话表存储。
- `EMBEDDING_PROVIDER` 支持 `openai` 与 `ollama`；默认使用 `openai`。
- Python 后端会在启动时自动读取 `python-ai-backend/.env`。
- 如果用根目录 `start-python-backend.bat` 启动，首次运行会在 `.env` 不存在时自动创建。
- `start-python-backend.bat` 只负责创建或修复 `.venv`、检查依赖、复制 `.env` 和启动服务，不会自动安装 `requirements.txt`。
- AI 面试会话表需要手工执行一次初始化 SQL：`sql/interview_schema.sql`。
- RAG 向量表需要手工执行一次初始化 SQL：`sql/pgvector_rag_schema.sql`。
- 仓库不会在应用启动时自动建表，避免一次性 SQL 混入运行时流程。
- 从 Python 配置回退逻辑看，最小必填可收敛为：`OPENAI_API_KEY`、`MYSQL_DATASOURCE_URL`、`PGVECTOR_DATASOURCE_URL`；但推荐把 `OPENAI_CHAT_MODEL`、`EMBEDDING_PROVIDER`、`OPENAI_EMBEDDING_MODEL`、`AUTOGEN_ENABLED` 也显式写出，便于排查。
- 如果 `EMBEDDING_PROVIDER=openai`，`OPENAI_EMBEDDING_BASE_URL` / `OPENAI_EMBEDDING_API_KEY` 不配时会回退到聊天或通用 `OPENAI_*`；如果切换到 `ollama`，则需要补 `OLLAMA_EMBEDDING_*`。
- `OPENAI_VISION_*` 用于图片 OCR，未单独配置时会回退到聊天或通用 `OPENAI_*`。
- `OPENAI_SPEECH_*` 用于音频转写，`OPENAI_REALTIME_*` 用于实时语音；不拆分供应商时也可以直接复用 `OPENAI_API_KEY`。

## 知识库使用说明

### 当前支持的文件类型

- 文档：`PDF / TXT / MD / DOCX`
- 图片：`PNG / JPG / JPEG / WEBP`
- 默认单文件大小限制：`10MB`
- 图片上传后会先经由 OCR 转成 Markdown，再和普通文档一样进入分块、Embedding、pgvector 入库链路

### 知识文档推荐写法

如果你是手工整理知识库内容，优先使用 `.md` 或 `.txt`，并按“标题块 + 内容块”方式编写。当前切分器会优先识别以下结构：

- Markdown 标题：`#`、`##`、`###`
- 编号标题：`1.`、`1)`、`1、`、`Q1:` 这类问题标题
- 问句标题：以 `?` 或 `？` 结尾的问题句
- 不同逻辑块之间请用空行分隔；空行是当前知识文档切分的重要边界

推荐示例：

```md
## 项目背景

这是一个面向校招和社招用户的简历编辑与 AI 面试项目，核心目标是降低简历整理和面试复盘成本。

## 你的职责

负责前端简历编辑器、模板系统、知识库上传入口和 Python AI 后端联调。

Q1: 为什么选择 pgvector 而不是把知识库存进 MySQL？

因为知识库需要做向量相似度检索，pgvector 更适合做 Embedding 存储和近邻召回；MySQL 继续只承接 AI 面试会话与消息历史。

Q2: 为什么 AI 面试要接入知识库？

因为项目背景、量化结果、技术选型和面试题答案可以先入库，再在面试轮次里按问题检索，减少模型脱离简历自由发挥。
```

这套写法同样适用于：

- 项目背景文档
- 项目亮点与量化结果文档
- 项目常见追问及标准回答
- Java / MySQL / Redis / MQ / 网络 / 操作系统等八股题资料

### 知识库有什么用

- 可以把你自己简历里的项目背景、技术方案、踩坑记录、量化结果、项目问答沉淀进去，让 AI 面试更贴近真实项目经历
- 可以把常见八股面试题、标准答案、追问链路整理后导入，用于后续模拟面试训练
- 对 `python-ai-backend` 来说，AI 面试会在每轮生成前先做一次向量检索，把命中的项目资料或题库片段注入上下文，减少回答太宽泛、离题或漂移
- 对知识库问答来说，同一批资料也可以复用于 `RAG` 检索与统一上传入口

## 常用脚本

```bash
# 本地开发
npm run dev

# 构建（含类型检查）
npm run build

# 仅构建前端产物
npm run build-only

# 预览构建结果
npm run preview

# 类型检查
npm run type-check

# 代码检查（自动修复）
npm run lint

# 格式化
npm run format
```

## 目录结构

```text
resume-builder/
  src/
    api/                         # 前端请求封装（chat/interview/speech/realtime）
      apiBase.ts                 # API 基础路径常量（/api）
    components/
      ai/                        # AI 配置、AI 优化、AI 面试、知识库界面
      common/                    # 通用组件（侧边栏、富文本等）
      resume/                    # 简历编辑器与预览
    services/
      prompts/                   # AI 提示词模板
      interview/                 # 面试类型定义
      aiOptimizeBackendService.ts
      interviewService.ts
      realtimeSpeechService.ts
    stores/
      resume.ts                  # 简历数据状态
      aiConfig.ts                # AI 配置状态
    templates/resume/            # 简历模板注册与实现
  sql/
    interview_schema.sql         # MySQL 会话表初始化脚本（手工执行一次）
    pgvector_rag_schema.sql      # pgvector 向量表初始化脚本（手工执行一次）
  spring-ai-backend/             # Spring Boot AI 后端
  python-ai-backend/             # FastAPI AI 后端
    app/
      api/                       # FastAPI 路由、Schema、Mapper、错误处理
      application/               # Use Case、应用服务、端口、DTO
      domain/                    # Chat / Interview / RAG 领域规则
      infrastructure/            # 配置、MySQL、pgvector、LLM、Agent 适配
      bootstrap/                 # 依赖装配
      shared/                    # SSE / NDJSON / 通用工具
    .env.example                 # Python 后端环境变量模板
    pyproject.toml               # Python 项目配置
  start-python-backend.bat       # Python 后端一键启动脚本
  start-python-backend.ps1       # Python 后端 PowerShell 启动脚本
  stop-python-backend.ps1        # Python 后端端口清理脚本
```

## 后端 API（摘要）

两套后端对外都保持同一套接口契约，基础路径均为 `'/api/ai'`，前端无需因为后端实现切换而改接口调用。

- `POST /chat`：普通问答
- `POST /chat/stream`：流式问答（SSE）
- `POST /audio/transcriptions`：音频转写
- `POST /realtime/client-secret`：实时语音临时密钥
- `POST /interview/turn/stream`：面试流式回合（NDJSON）
- `GET /interview/sessions`：面试会话列表
- `GET /interview/sessions/{sessionId}`：会话详情
- `POST /rag/query`：RAG 检索问答
- `POST /rag/documents`：RAG 文档入库
- `POST /rag/upload`：知识库统一上传入口，支持 `PDF/TXT/MD/DOCX/PNG/JPG/JPEG/WEBP`

更多后端细节见：

- [spring-ai-backend/README.md](spring-ai-backend/README.md)
- [python-ai-backend/README.md](python-ai-backend/README.md)

## 数据库初始化

本地联调推荐先启动 `spring-ai-backend/docker-compose.yml`，再手工导入数据库脚本：

- `sql/interview_schema.sql`：AI 面试会话表，Spring / Python 后端共用
- `sql/pgvector_rag_schema.sql`：RAG chunk 与向量表，知识库功能使用

在 `spring-ai-backend/` 目录执行：

```bash
docker compose up -d
docker exec -i spring-ai-mysql mysql -uroot -proot resume-builder < ../sql/interview_schema.sql
docker exec -i spring-ai-pgvector psql -U postgres -d resume_builder_vector < ../sql/pgvector_rag_schema.sql
```

说明：

- MySQL 会话表是 AI 面试必需依赖，pgvector 表只在使用 RAG / OCR 入库时需要。
- 所有一次性 SQL 都需要开发者手工执行，应用启动时不会自动执行。
- PostgreSQL + pgvector 仍然只用于 RAG，不用于会话表存储。

## 内置 Codex Skills

项目内置技能目录：`.codex/skills/`

- `resume-template-from-image`
- `resume-backend-project-optimizer`
- `resume-interview-coach`

### `resume-template-from-image` 使用说明

这个 skill 的用途是：你给一张简历模板图片，Codex 按当前项目模板规范直接生成一套可切换的新模板。

使用它时不需要启动后端，也不需要启动 MySQL / pgvector；如果你想立刻在页面里预览生成结果，只需要启动前端即可。

推荐使用方式：

1. 在仓库根目录启动前端：`npm run dev`
2. 在 Codex 对话里发送模板图片，并明确给出模板名称
3. 如果你愿意，也可以顺手给出模板 key；不提供时会自动生成 kebab-case key
4. Codex 会按项目规范直接生成并接入以下文件：
   - `src/templates/resume/<key>/ResumeTemplate.vue`
   - `src/templates/resume/<key>/template.ts`
   - `src/assets/templates/resume/<key>-preview.svg`
   - `src/templates/resume/index.ts`
5. 回到前端页面刷新后，就可以在模板选择器里直接切换和预览

建议提示词示例：

```text
请使用 resume-template-from-image，根据我上传的图片生成一个新的简历模板。
模板名称：深蓝商务模板
模板 key：deep-blue-business
要求：保持 A4 预览兼容，接入当前模板注册体系。
```

## Harness Workflow

仓库级 Harness Engineering 工作流见 [docs/harness-engineering-workflow.md](docs/harness-engineering-workflow.md)。

## 友情链接

- [Linux.do](https://linux.do/)

## License

MIT

## Python Backend 启动说明

- `start-python-backend.bat` 会优先复用已有的 `python-ai-backend/.venv`，必要时重新创建虚拟环境。
- 该脚本不会自动安装 `requirements.txt` 或 `requirements-optional.txt`；首次运行前请先手工执行 `uv pip install`。
- 脚本会检查核心依赖、补 `.env`、清理 `8999` 端口占用并启动 `uvicorn`。
- 如果需要彻底重装依赖，删除 `python-ai-backend/.venv` 后重新运行 `start-python-backend.bat` 即可。
