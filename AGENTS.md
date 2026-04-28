<!-- author: jf -->
# AI 执行规范

## `.rules` 规则文档引用（强制）

1. 处理本仓库任务时，必须先阅读并遵守 `.rules/` 目录下的规则文档。
2. `.rules/` 下规则文档与本文件共同构成仓库级强制约束；如无更高优先级用户指令，不得绕过。
3. 当前必须遵守的规则文档如下：
   - `.rules/python-ai-backend-mandatory-rules.md`
   - `.rules/harness-mcp-workflow-rules.md`
4. 若后续 `.rules/` 目录新增规则文档，默认同样属于必须遵守的仓库规则；执行任务前应一并读取。

本规范适用于本仓库内所有 AI 协作与自动化改动。

## 测试代码约束（强制）

1. 禁止在项目中新增任何测试代码。
2. 禁止修改现有测试代码。
3. 禁止为测试目的新增以下内容：
   - `src/test`、`__tests__`、`tests` 目录下任何文件
   - `*.test.*`、`*.spec.*` 文件
   - 测试专用脚本、测试夹具（fixture）、测试桩（mock）文件
4. 禁止为了验证问题而提交“临时测试代码”。

## 数据库与 Mapper SQL 约束（强制）

1. 后端运行代码中禁止写死 PostgreSQL、MySQL 或其他数据库 SQL 字符串，包括 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`CREATE`、`ALTER`、`DROP`、索引初始化等语句。
2. MySQL 如确需自定义业务 SQL，必须写在 `mapper.xml` 文件中，不允许直接写在 Mapper 接口注解里（如 `@Select`、`@Update`、`@Insert`、`@Delete`），也不允许写在 Controller、Service、Config 或其他 Java 代码中。
3. Spring AI 后端 Java `mapper/` 目录只允许存放带 `@Mapper` 的 Mapper 接口；MyBatis 查询投影、结果行对象、Row/Projection 类必须放入 `entity/`，对外 API 模型才放入 `dto/`。
4. PostgreSQL + pgvector 向量库存储与相似度检索必须优先使用 Spring AI `VectorStore` / `PgVectorStore` 提供的 `add`、`similaritySearch` 等能力，禁止在后端代码中手写 pgvector 插入、检索或建表 SQL。
5. 建表、索引、初始化等一次性 SQL（非项目运行期业务逻辑）必须写入固定 SQL 目录下的独立 `.sql` 文件，固定 SQL 目录为：`sql/`。
6. 禁止在应用启动流程中执行项目自写的一次性 SQL，也禁止 Spring AI `PgVectorStore` 自动建表；pgvector 表必须由开发者手工执行 `sql/pgvector_rag_schema.sql` 创建，Spring AI 后端必须保持 `initializeSchema(false)`。

## 会话存储数据库约束（强制）

1. AI 面试会话存储数据库固定为 MySQL。
2. PostgreSQL 仅用于向量存储（pgvector）相关能力，不用于会话表存储。
3. 会话建表脚本仅保留一份：`sql/interview_schema.sql`。
4. MySQL 面试会话表和 pgvector RAG 向量表都禁止应用启动自动建表，仍由开发者手工执行 `sql/interview_schema.sql` 与 `sql/pgvector_rag_schema.sql`。

## 文件作者标识约束（强制）

1. 除 `mapper.xml` 外，新增或修改的文件必须标记作者信息（如注释头、元数据）。
2. 作者必须为 `jf`。
3. 禁止出现作者为 `ai` 的标识（包括 `author: ai`、`作者：ai`、`created by ai` 等）。

## 允许的验证方式（不改项目代码）

1. 运行现有命令进行验证（不新增文件、不改源码）：
   - `npm run type-check`
   - `npm run lint`
   - `npm run build` 或 `npm run build-only`
2. 本地手工验证（UI 操作、接口调用、日志观察）。
3. 一次性命令行验证（不落盘到项目文件，不生成新代码文件）。

## 提交流程要求

1. 所有功能修复与优化，不得以“补测试代码”作为交付前置条件。
2. 变更说明中必须记录验证方式与验证结果。
3. 评审发现测试代码变更时，必须先移除再继续评审。

## 协作参考文档

1. `docs/harness-engineering-workflow.md`
   - 仓库级 Harness Engineering 工作流，适用于任务路由、知识回写、熵治理与跨前后端协作时参考。

## MCP 使用要求

1. 涉及 OpenAI 能力、官方文档、模型选择、API 迁移与 SDK 接入时，必须优先按 `.rules/harness-mcp-workflow-rules.md` 使用 `openaiDeveloperDocs`。
2. 涉及前端页面、交互、模板、流式渲染与视觉验证时，必须优先按 `.rules/harness-mcp-workflow-rules.md` 使用 `playwright`。
3. 涉及 PR、Issue、Review、Checks 与远程协作上下文时，必须优先按 `.rules/harness-mcp-workflow-rules.md` 使用 `github`。
4. `memory` 只能用于长期个人偏好，不得替代仓库规则、接口契约与项目事实。

## 新功能开发要求

1. 新功能、行为变更或多步骤优化任务，必须先按 `.rules/harness-mcp-workflow-rules.md` 输出细化任务清单，不得直接跳过拆分进入实现。
2. 用户需求不清晰时，必须先提供一版初步任务 todo list 让用户澄清或确认。
3. 在用户确认细化任务后，必须先生成验收细节 list 与需求文档 `.md`，再开始顺序执行。
4. 执行时必须按细化任务顺序逐条完成，并在需求文档中同步标记状态。
5. 全部细化任务完成后，必须按验收细节 list 对每一项给出 `通过` 或 `不通过` 结论；存在 `不通过` 时不得声称完成，必须修正并重新进行全量验收。
