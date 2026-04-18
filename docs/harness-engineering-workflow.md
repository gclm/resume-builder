<!-- author: jf -->
# Resume Builder Harness Engineering 工作流

> 参考：OpenAI 于 2026 年 2 月 11 日发布的《Harness Engineering》  
> 原文：https://openai.com/zh-Hans-CN/index/harness-engineering/

## 1. 目标

这份工作流用于把 `resume-builder` 的协作方式从“临时指令驱动”升级为“仓库知识驱动”：

1. 由人负责目标、边界、优先级与验收。
2. 由代理负责检索、实现、验证、回写知识与清理熵增。
3. 让前端、Python AI 后端、Spring AI 后端在同一套仓库规则下稳定协作。

## 2. 当前项目的 Harness 基座

当前仓库已经具备做 Harness Engineering 的基础骨架，后续任务都应优先复用，而不是绕开：

1. 规则入口固定为 `AGENTS.md` -> `.rules/`。
2. 产品总图和启动说明固定为 `README.md`。
3. 前端固定在 `src/`，职责围绕简历编辑、AI 优化、AI 面试。
4. Python AI 后端固定在 `python-ai-backend/`，采用 `api -> application -> domain <- infrastructure` 边界。
5. Spring AI 后端固定在 `spring-ai-backend/`，采用 `controller / service / mapper / entity / dto / config / exception / cleaner` 边界。
6. 前后端统一接口契约固定为 `'/api/ai/*'`，切换后端实现时前端不改接口路径。
7. AI 面试会话数据固定落 MySQL，RAG 向量检索固定落 PostgreSQL + pgvector。
8. 会话建表脚本固定只有一份：`sql/interview_schema.sql`。
9. 联调端口固定为 `8999`，`spring-ai-backend` 和 `python-ai-backend` 同时只能启动一个。

## 3. 核心原则

### 3.1 人类负责方向，代理负责闭环

人类至少定义四件事：

1. 目标是什么。
2. 范围到哪里为止。
3. 成功标准是什么。
4. 优先级与取舍是什么。

代理负责把任务闭环到仓库内：

1. 读取规则和现有实现。
2. 找到最小修改面。
3. 产出代码或文档。
4. 给出验证方式与结果。
5. 把稳定知识回写到仓库，而不是只留在对话里。

### 3.2 仓库内知识是系统记录

符合 Harness Engineering 的做法不是“靠代理记住项目”，而是把长期有效的信息写回仓库：

1. 新的模块边界，回写到规则或模块 README。
2. 新的启动方式，回写到根 README 或子模块 README。
3. 新的协作流程，回写到 `docs/` 或入口文档。
4. 新的兼容性约束，回写到离代码最近的位置。

### 3.3 采用 Progressive Disclosure

所有任务默认按下面顺序加载上下文，避免一上来把整个仓库塞满：

1. `AGENTS.md`
2. `.rules/` 中与任务范围直接相关的规则
3. 根 `README.md`
4. 对应子模块 `README.md`
5. 相关目录结构
6. 最小必要代码文件

### 3.4 边界优先于速度

这个仓库的高价值不在“先跑起来”，而在“前后端、双后端和数据边界始终可维护”：

1. 前端 `api/` 只放请求定义，业务编排放 `services/`。
2. Python AI 后端必须守住 `api -> application -> domain <- infrastructure`。
3. Spring AI 后端必须守住 `controller -> service -> mapper -> entity` 的职责分工。
4. 业务 SQL 必须进 `mapper.xml`，不能散落到 Java 注解或 Service 中。
5. 会话存储不能漂移到 pgvector，RAG 检索不能挤进 MySQL 会话表。

### 3.5 失败要转化为 Harness 改进

如果某类问题反复出现，不应只靠再次提醒解决，而应直接补 Harness：

1. 代理反复读错边界，就补规则或目录说明。
2. 代理反复启动错后端，就补 README 的启动路由说明。
3. 代理反复误用数据源，就补数据职责说明或脚本提示。
4. 代理反复改坏契约，就补接口契约检查清单。

### 3.6 持续做熵治理

随着任务变多，仓库会自然长出重复文档、重复说明、重复能力实现。工作流必须主动清理：

1. 删除过期说明，避免一处写新一处写旧。
2. 合并重复的启动文档和约束文档。
3. 把重复的“隐性规则”提升成显性规则。
4. 把高频排障步骤沉淀为固定 runbook。

## 4. 任务路由

### 4.1 文档与规则任务

适用范围：

1. `AGENTS.md`
2. `.rules/`
3. `README.md`
4. `docs/`
5. 子模块 `README.md`

处理方式：

1. 先确定这是不是“长期知识”，只有长期知识才入仓。
2. 优先修改入口文档和最靠近实现的文档，避免新建平行说明。
3. 新文档必须能被入口文档发现。

### 4.2 前端任务

适用范围：

1. `src/components/`
2. `src/services/`
3. `src/api/`
4. `src/stores/`
5. `src/templates/`

标准流程：

1. 先确认是页面、状态、服务还是接口问题。
2. 先保住现有产品主线：简历编辑、AI 优化、AI 面试。
3. 先保住 `api/` 与 `services/` 边界，再动组件。
4. 只有页面和交互发生稳定变化时，才更新截图或文档。

### 4.3 Python AI 后端任务

适用范围：

1. `python-ai-backend/app/api/`
2. `python-ai-backend/app/application/`
3. `python-ai-backend/app/domain/`
4. `python-ai-backend/app/infrastructure/`
5. `python-ai-backend/app/bootstrap/`

标准流程：

1. 先判断变更属于接口适配、用例编排、领域规则还是外部依赖实现。
2. 先确认是否影响 `'/api/ai/*'` 契约。
3. 先确认是否影响 MySQL 会话存储或 pgvector 检索职责。
4. 只有稳定变化才回写到 `python-ai-backend/README.md`。

### 4.4 Spring AI 后端任务

适用范围：

1. `spring-ai-backend/src/main/java/.../controller`
2. `spring-ai-backend/src/main/java/.../service`
3. `spring-ai-backend/src/main/java/.../mapper`
4. `spring-ai-backend/src/main/resources/mapper`
5. `spring-ai-backend/sql/`

标准流程：

1. 先确认是控制器、服务、持久化还是配置变更。
2. 涉及业务 SQL 时，先落 `mapper.xml`，再接 `Mapper` 和 `Service`。
3. 涉及接口行为时，先守住与前端、Python 后端的契约一致性。
4. 只有稳定变化才回写到 `spring-ai-backend/README.md`。

### 4.5 跨栈任务

适用范围：

1. 前端与任一后端协同改动
2. 两套后端的契约对齐
3. 会话存储、RAG、语音、Realtime 等共享能力调整

标准流程：

1. 先从契约开始，不要先从实现细节开始。
2. 先明确哪一层是源头变更，哪一层只做适配。
3. 先改公共约束，再改具体实现。
4. 最后补文档，说明前端、Python、Spring 三方如何保持一致。

## 5. 标准执行工作流

### 第 1 步：任务受理

每个任务先落成一张简化任务卡：

1. 目标
2. 影响范围
3. 非目标
4. 验收标准
5. 验证方式

### 第 2 步：上下文装载

默认只加载完成任务必需的上下文：

1. 规则入口
2. 模块 README
3. 相关目录
4. 最小必要代码

不允许一开始就无差别读取整个仓库。

### 第 3 步：确定任务车道

根据变更范围把任务归入一个主车道：

1. 文档
2. 前端
3. Python AI 后端
4. Spring AI 后端
5. 跨栈

如果是跨栈任务，也必须先定义“主车道”，避免多头并行却没有主线。

### 第 4 步：定义最小可交付切片

每次只交付一个最小闭环：

1. 一个页面问题
2. 一个接口契约变化
3. 一个用例编排修复
4. 一个持久化链路修复
5. 一份稳定文档沉淀

避免把 UI、接口、数据库、文档、架构调整混成一次大改。

### 第 5 步：实现

实现顺序遵循“边界先于细节”的原则：

1. 先改契约或边界。
2. 再改业务编排。
3. 再改存储和外部依赖。
4. 最后改展示层和说明文档。

### 第 6 步：验证

验证只使用仓库允许的方式：

1. 文档任务：做结构、链接、入口可发现性自检。
2. 前端任务：按规则执行 `npm run lint`，必要时补 `npm run type-check` 或 `npm run build`。
3. Python AI 后端任务：优先做启动链路、健康检查、接口手工验证，不新增测试代码。
4. Spring AI 后端任务：优先做启动链路、健康检查、接口手工验证，不新增测试代码。
5. 跨栈任务：补契约一致性检查，确认两套后端与前端行为未漂移。

### 第 7 步：知识回写

只要任务沉淀出长期有效知识，必须立刻回写：

1. 改启动方式，更新 README。
2. 改目录职责，更新规则文档。
3. 改协作流程，更新 `docs/` 或入口文档。
4. 改共享契约，更新前后端双方说明。

### 第 8 步：审查与合并

如果任务需要提交代码，必须遵守仓库已有审查流程：

1. `git commit` 前先问是否执行 `code-review`。
2. 用户确认后，执行 `code-review` 并反馈结论。
3. Review 结束后，再问是否修复问题。
4. 用户确认后，再执行 `code-review-fix`。

## 6. 项目级 DoD

任务完成前，至少要满足下面条件：

1. 没有绕过 `AGENTS.md` 和 `.rules/`。
2. 没有破坏前端、Python、Spring 的既有分层边界。
3. 没有破坏 `'/api/ai/*'` 统一契约。
4. 没有破坏 MySQL 与 pgvector 的职责分离。
5. 没有引入与主业务无关的页面、接口或目录。
6. 没有新增测试代码。
7. 相关长期知识已经回写到仓库。

## 7. 推荐的固定节奏

### 每日

1. 清理当天任务里新增的临时说明。
2. 把对话里出现但仓库里没有的稳定知识回写。
3. 检查是否出现新的重复入口文档。

### 每周

1. 复查前端与双后端的契约是否漂移。
2. 复查 `README.md`、子模块 README 与规则文档是否一致。
3. 复查是否存在“代理反复犯同一类错”的情况，并把问题转化为 Harness 补强项。

### 每月

1. 评估哪些文档已经过期。
2. 评估哪些目录职责已经模糊。
3. 评估哪些高频排障步骤值得沉淀成脚本或 runbook。

## 8. 下一阶段建议补强项

为了让这个仓库更接近 OpenAI 所说的 Harness Engineering，建议后续按优先级推进下面几项：

1. 增加一个仓库级文档索引，明确“规则、运行、架构、排障、工作流”五类入口。
2. 增加契约一致性清单，专门覆盖前端、Python、Spring 三方的 `/api/ai/*` 行为。
3. 增加面向代理的排障 runbook，固定记录 `8999` 端口、健康检查、MySQL、pgvector、Realtime 常见故障。
4. 增加轻量化的文档巡检流程，防止 README、规则、实现长期漂移。
5. 为双后端补一份“能力对齐矩阵”，避免一套后端先演进，另一套后端失去可替换性。

## 9. 建议使用的任务卡模板

```md
## 任务卡

- 目标：
- 主车道：文档 / 前端 / Python AI 后端 / Spring AI 后端 / 跨栈
- 影响范围：
- 非目标：
- 入口文档：
- 验收标准：
- 验证方式：
- 需要回写的知识：
```
