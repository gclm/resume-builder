<!-- author: jf -->
# Resume Builder

一个基于 Vue 3 + Vite 的简历编辑与 AI 面试一体化项目，当前同时支持 `spring-ai-backend` 和 `python-ai-backend` 两套后端实现，覆盖简历优化、AI 面试、流式回复、语音输入与会话存储。

## 功能概览

### 1) 简历编辑
- 模块化编辑：基本信息、教育经历、专业技能、工作经历、项目经历、荣誉奖项、个人简介
- 模块可见性开关与顺序调整（`basicInfo` 固定首位）
- 自动本地保存与手动保存草稿
- 模板切换（当前内置 8 套模板）
- 导出能力：高清 PDF、压缩 PDF、Markdown

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

### 方式 A：仅启动前端

```bash
npm install
npm run dev
```

默认地址：`http://localhost:5173`

### 方式 B：前后端联调（推荐）

前端开发代理固定转发到 `http://localhost:8999`，所以联调时只需要在 `spring-ai-backend` 和 `python-ai-backend` 中二选一启动即可，不要同时启动两个后端。

1. 启动前端（项目根目录）：

```bash
npm install
npm run dev
```

2. 选择一种后端启动方式。

#### 方案 B1：启动 Spring AI 后端

在 `spring-ai-backend/` 目录执行：

```bash
cp .env.example .env
mysql -u root -p your_database < ../sql/interview_schema.sql
docker compose up -d
mvn spring-boot:run
```

更多说明见 [spring-ai-backend/README.md](spring-ai-backend/README.md)。

#### 方案 B2：启动 Python AI 后端

推荐直接在项目根目录双击或执行：

```bash
start-python-backend.bat
```

这个脚本会自动完成以下动作：

- 创建 `python-ai-backend/.venv`
- 安装 `requirements.txt` 和可选 AI 依赖
- 若缺少 `.env`，自动从 `python-ai-backend/.env.example` 复制生成
- 先清理旧的 `8999` 端口监听，再启动 `uvicorn`

首次联调前，还需要先手工执行一次会话建表脚本：

```bash
mysql -u root -p your_database < sql/interview_schema.sql
```

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

#### Spring AI 后端

模板文件：`spring-ai-backend/.env.example`

最小可用配置（`.env`）：

```bash
OPENAI_API_KEY=your_api_key_here
MYSQL_DATASOURCE_URL=jdbc:mysql://localhost:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5432/resume_builder_vector
PGVECTOR_DATASOURCE_USERNAME=postgres
PGVECTOR_DATASOURCE_PASSWORD=postgres
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
```

可选分路配置（不同模型/供应商）：

- Chat：`OPENAI_CHAT_BASE_URL`、`OPENAI_CHAT_API_KEY`、`OPENAI_CHAT_MODEL`
- Speech：`OPENAI_SPEECH_BASE_URL`、`OPENAI_SPEECH_API_KEY`
- Realtime：`OPENAI_REALTIME_BASE_URL`、`OPENAI_REALTIME_API_KEY`
- Embedding：`OPENAI_EMBEDDING_BASE_URL`、`OPENAI_EMBEDDING_API_KEY`、`OPENAI_EMBEDDING_MODEL`

`application.yml` 已通过 `spring.config.import=optional:file:.env[.properties]` 自动加载 `.env`，无需把密钥写入源码。

#### Python AI 后端

模板文件：`python-ai-backend/.env.example`

常用配置项：

```bash
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
APP_RAG_TOP_K=5

OPENAI_BASE_URL=https://api.openai.com
OPENAI_API_KEY=your_api_key_here
OPENAI_CHAT_MODEL=gpt-5.4
OPENAI_CHAT_COMPLETIONS_PATH=/v1/chat/completions

MYSQL_DATASOURCE_URL=mysql+pymysql://root:root@127.0.0.1:3306/resume-builder
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root

PGVECTOR_DATASOURCE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resume_builder_vector

AUTOGEN_ENABLED=false
```

说明：

- MySQL 只负责 AI 面试会话与消息历史存储。
- PostgreSQL + pgvector 只负责 RAG 向量检索，不用于会话表存储。
- Python 后端会在启动时自动读取 `python-ai-backend/.env`。
- 如果用根目录 `start-python-backend.bat` 启动，首次运行会在 `.env` 不存在时自动创建。
- AI 面试会话表需要手工执行一次初始化 SQL：`sql/interview_schema.sql`。
- 仓库不会在应用启动时自动建表，避免一次性 SQL 混入运行时流程。

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
      ai/                        # AI 配置、AI 优化、AI 面试界面
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

更多后端细节见：

- [spring-ai-backend/README.md](spring-ai-backend/README.md)
- [python-ai-backend/README.md](python-ai-backend/README.md)

## 数据库初始化

AI 面试会话相关表统一使用 MySQL，且只保留一份建表脚本：

`sql/interview_schema.sql`

执行方式：

```bash
mysql -u root -p your_database < sql/interview_schema.sql
```

说明：

- 这份 SQL 同时适用于 `spring-ai-backend` 和 `python-ai-backend`。
- 只需要手工执行一次，不会在应用启动时自动执行。
- PostgreSQL + pgvector 仍然只用于 RAG，不用于会话表存储。

## 内置 Codex Skills

项目内置技能目录：`.codex/skills/`

- `resume-template-from-image`
- `resume-backend-project-optimizer`
- `resume-interview-coach`

## Harness Workflow

仓库级 Harness Engineering 工作流见 [docs/harness-engineering-workflow.md](docs/harness-engineering-workflow.md)。

## 友情链接

- [Linux.do](https://linux.do/)

## License

MIT
