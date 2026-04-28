<!-- author: jf -->
# Resume Builder 后端强制规则

## 1. 规则定位

本文档用于定义 `resume-builder` 仓库后端范围内的产品背景、后端目标、目录扩展边界、文件拆分要求、数据库约束与 AI 执行限制。

本仓库后端不是普通的示例 API 工程，而是一个服务 **简历编辑、简历优化、AI 面试** 场景的 AI 业务后端，目标是帮助求职者更快、更精准地完成简历优化、模拟面试与面试准备。

凡涉及 `python-ai-backend/`、`spring-ai-backend/` 的新增、修改、重构、迁移、目录调整、接口实现、AI 能力编排与数据库相关变更，默认都必须遵守本文档。

注意：
- 本文档位于 `.rules/` 下，属于仓库级强制规则，不视为普通说明文档。
- 本文档是后端通用规则；涉及 `python-ai-backend/` 与 `spring-ai-backend/` 时，还必须同时遵守对应专项规则。
- 如当前实现与本文档冲突，后续改动应优先向本文档靠拢；如确需例外，应先更新规则文档，再改代码。

---

## 2. 产品背景与后端目标

后端必须始终围绕以下业务目标展开：

1. 简历优化
   - 支持简历内容润色、结构化表达优化与问答生成。
   - 输出必须服务真实求职和面试场景，而不是生成空泛内容。

2. AI 面试
   - 支持面试回合推进、追问、评分、总结与会话保存。
   - 保证会话链路、状态推进与数据存储稳定可维护。

3. RAG、语音与 Realtime
   - 支持知识检索、音频转写、Realtime 能力与相关上游集成。
   - 各能力都应服务求职者提升面试效率这一核心目标。

4. 前后端协作
   - 后端接口设计、数据结构和能力拆分必须服务当前前端，不得演变为脱离主业务的泛化示例工程。

---

## 3. 后端执行原则

### 3.1 规则读取要求

1. 处理后端任务时，必须先阅读并遵守 `.rules/` 下与后端相关的规则文档。
2. `.rules/` 下规则文档与 `AGENTS.md` 共同构成仓库级强制约束；如无更高优先级用户指令，不得绕过。
3. 后端改动除遵守本文档外，还必须同步遵守 `.rules/global-rules.md` 与 `.rules/code-conventions.md`。

### 3.2 文件作者标识约束

1. 除 `mapper.xml` 外，新增或修改的后端文件必须标记作者信息，例如注释头或元数据。
2. 作者必须为 `jf`。
3. 禁止出现作者为 `ai` 的标识，包括但不限于 `author: ai`、`作者：ai`、`created by ai`。

### 3.3 目标导向原则

1. 后端必须服务简历优化、AI 面试、RAG、语音与相关会话能力。
2. 禁止生成与主业务无关的后端模块、接口与目录。
3. 新增能力必须与现有目录职责、接口语义和分层边界保持一致。

---

## 4. 后端通用强制规则

### 4.1 文件体积与职责拆分

1. 后端代码编写时，每个文件不得超过 `800` 行。
2. 超过 `800` 行时，必须按职责、业务能力或模块边界拆分到不同文件。
3. 禁止把多个业务能力、多个流程阶段、多个职责全部堆在同一个后端文件中。

### 4.2 目录扩展约束

1. 后端分层必须优先遵守现有项目结构。
2. 禁止在已有分层之外，随意在外层新增新的平级目录。
3. 如需扩展，优先在现有层内新增子包或子目录；Spring AI 后端如需承接非业务编排支撑类，必须使用专项规则中列明的外层职责目录。
4. 无规则支撑时，不得新增语义模糊或破坏分层的目录。
5. 禁止使用 `common`、`utils`、`helper`、`manager`、`misc` 等大杂烩目录承接职责不清的后端文件。

### 4.3 功能归属约束

1. 禁止在非该功能目录下新增非对应功能的文件。
2. 聊天、面试、RAG、音频、Realtime、简历优化等能力，应各自落在对应功能目录和分层中。
3. 公共能力仅在确实跨模块复用时才能抽取，禁止借“公共封装”名义制造大杂烩目录。
4. Spring AI 后端 `service/` 目录只能放真正 `@Service` 业务编排类；非 `@Service` 文件必须按职责放到专项规则列明的外层目录。

---

## 5. Python AI 后端协作规则

`python-ai-backend/` 的功能边界、目录职责与依赖方向，必须严格遵守 `.rules/python-ai-backend-mandatory-rules.md`。

额外要求：
- 禁止因为临时功能开发，绕开既有 `api -> application -> domain <- infrastructure` 依赖边界。
- 禁止把本应属于 `application`、`domain` 或 `infrastructure` 的职责重新混入路由层。
- 禁止在无规则支撑的情况下新增破坏分层的新顶层模块。

---

## 6. Spring AI 后端补充强制规则

除 `.rules/spring-ai-backend-mandatory-rules.md` 外，还必须额外满足以下项目级要求：

### 6.1 Controller 边界

1. `controller` 层只负责接口对接、参数接收、响应返回和少量必要的逻辑校验。
2. `controller` 层必须保持简洁。
3. 禁止在 `controller` 中编写过多业务逻辑、复杂流程控制、长链路编排、SQL 访问或模型调用细节。

### 6.2 Java 开发规范

1. `spring-ai-backend/` 代码生成必须严格遵守《阿里巴巴 Java 开发手册》。
2. 命名、常量、空值处理、日志、异常、集合使用、并发、数据库访问、事务、代码分层等，都不得违反该手册的核心规范。
3. 每次生成或修改 Spring AI 后端代码后，必须对照《阿里巴巴 Java 开发手册》进行自检。
4. 如发现不符合项，应先修正再交付。

### 6.3 Spring AI Service 目录强制边界

1. `spring-ai-backend/src/main/java/com/resumebuilder/springaibackend/service/` 只允许存放真正带 `@Service` 注解、且承担业务用例或流程编排职责的类。
2. 没有 `@Service` 注解的 Java 文件一律不得放入 `service/`。
3. `@Service` 不是放入 `service/` 的充分条件；如果主要职责是 SDK client、HTTP client support、provider adapter、VectorStore 适配、pgvector repository、Embedding provider、OCR 实现、WebSocket handler、parser、chunker、support/helper，则必须放入对应外层职责目录。
4. Spring AI 后端允许使用的非业务编排外层职责目录，以 `.rules/spring-ai-backend-mandatory-rules.md` 为准，当前包括 `client/`、`vector/`、`embedding/`、`ocr/`、`realtime/`、`parser/`、`chunking/`。
5. 禁止为了把支撑类留在 `service/` 中而随意添加 `@Service` 注解。

---

## 7. 数据库与 SQL 强制约束

1. 后端运行代码中禁止写死 PostgreSQL、MySQL 或其他数据库 SQL 字符串，包括 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`CREATE`、`ALTER`、`DROP`、索引初始化等语句。
2. MySQL 如确需自定义业务 SQL，必须写在 `mapper.xml` 文件中，不允许直接写在 Mapper 接口注解里，例如 `@Select`、`@Update`、`@Insert`、`@Delete`，也不允许写在 Controller、Service、Config 或其他 Java 代码中。
3. Spring AI 后端 Java `mapper/` 目录只允许存放带 `@Mapper` 的 Mapper 接口；MyBatis 查询投影、结果行对象、Row/Projection 类必须放入 `entity/`，对外 API 模型才放入 `dto/`。
4. PostgreSQL + pgvector 向量库存储与相似度检索必须优先使用 Spring AI `VectorStore` / `PgVectorStore` 提供的 `add`、`similaritySearch` 等能力，禁止在后端代码中手写 pgvector 插入、检索或建表 SQL。
5. 建表、索引、初始化等一次性 SQL（非项目运行期业务逻辑）必须写入固定 SQL 目录下的独立 `.sql` 文件，固定 SQL 目录为：`sql/`。
6. 禁止在应用启动流程中执行项目自写的一次性 SQL，也禁止 Spring AI `PgVectorStore` 自动建表；pgvector 表必须由开发者手工执行 `sql/pgvector_rag_schema.sql` 创建，Spring AI 后端必须保持 `initializeSchema(false)`。

---

## 8. 会话存储数据库约束

1. AI 面试会话存储数据库固定为 MySQL。
2. PostgreSQL 仅用于向量存储（pgvector）相关能力，不用于会话表存储。
3. 会话建表脚本仅保留一份：`sql/interview_schema.sql`。
4. MySQL 面试会话表和 pgvector RAG 向量表都禁止应用启动自动建表，仍由开发者手工执行 `sql/interview_schema.sql` 与 `sql/pgvector_rag_schema.sql`。

---

## 9. 测试代码约束

1. 禁止在项目中新增任何测试代码。
2. 禁止修改现有测试代码。
3. 禁止为测试目的新增以下内容：
   - `src/test`、`__tests__`、`tests` 目录下任何文件
   - `*.test.*`、`*.spec.*` 文件
   - 测试专用脚本、测试夹具（fixture）、测试桩（mock）文件
4. 禁止为了验证问题而提交“临时测试代码”。

---

## 10. 允许的验证方式

允许使用以下方式验证，但不得通过新增测试代码完成验证：

1. 运行现有命令进行验证，不新增文件、不改测试源码：
   - `npm run type-check`
   - `npm run lint`
   - `npm run build`
   - `npm run build-only`
2. 本地手工验证，例如 UI 操作、接口调用、日志观察。
3. 一次性命令行验证，不落盘到项目文件，不生成新代码文件。

---

## 11. 提交流程要求

1. 所有功能修复与优化，不得以“补测试代码”作为交付前置条件。
2. 变更说明中必须记录验证方式与验证结果。
3. 评审发现测试代码变更时，必须先移除再继续评审。

---

## 12. 结论

后端的一切改动，都必须服务“帮助求职者更快、更精准地进行面试并提升通关效率”这一核心目标。

因此必须同时保证：

- 产品方向不跑偏。
- 分层边界不被破坏。
- 文件职责不堆叠。
- 数据库职责不越界。
- SQL 存放位置清晰。
- AI 产出的后端代码可持续维护。
