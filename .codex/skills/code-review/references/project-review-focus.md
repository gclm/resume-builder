<!-- author: jf -->
# Resume Builder 项目审查重点

## 技术栈概览

- 前端：Vue 3 + TypeScript + Vite
- 前端目录：`src/**`
- Python AI 后端：`python-ai-backend/**`
- Spring AI 后端：`spring-ai-backend/**`
- 仓库规则：`.rules/**` 与 `AGENTS.md`

## 高风险区域

1. 前端目录边界
   - `src/api/**` 是否只定义请求，不夹带业务逻辑。
   - 业务编排是否正确落在 `src/services/**`。
   - 是否在错误目录下新增了不属于该功能的文件。

2. 前端页面与模板一致性
   - 新页面或新模块是否遵守当前主题风格、颜色配比和样式规范。
   - 是否出现与现有简历模板体系不一致的随机风格页面。
   - 单个前端文件是否超过 `1000` 行且未拆分。

3. 简历编辑与 AI 交互链路
   - 简历编辑、模板预览、AI 优化、AI 面试之间的数据流是否一致。
   - 流式返回、会话状态和错误提示是否会导致 UI 状态错乱。

4. Python AI 后端分层
   - 是否破坏 `api -> application -> domain <- infrastructure` 依赖边界。
   - 路由层是否混入业务逻辑、数据库访问或外部能力编排。

5. Spring AI 后端分层
   - `controller` 是否只保留接口对接与少量参数校验。
   - 业务 SQL 是否全部落在 `mapper.xml`，是否误用 `@Select`、`@Update`、`@Insert`、`@Delete`。
   - 单个后端文件是否超过 `800` 行且未按职责拆分。

6. 数据库职责
   - AI 面试会话是否固定使用 MySQL，而不是错误落到 PostgreSQL。
   - 会话建表脚本是否仍然只有 `spring-ai-backend/sql/interview_schema.sql` 一份。
   - 是否出现启动时自动执行一次性 SQL 的行为。

7. 仓库规则符合性
   - 是否新增或修改了测试代码。
   - 新增文件是否包含作者 `jf` 标识。
   - 是否违反 `.rules/frontend-mandatory-rules.md`、`.rules/backend-mandatory-rules.md`、`.rules/python-ai-backend-mandatory-rules.md` 或 `.rules/spring-ai-backend-mandatory-rules.md`。

## 建议检索命令

- `npm run type-check`
- `npm run lint`
- `rg -n "src/api|src/services|fetch\\(|axios" src`
- `rg -n "@Select|@Update|@Insert|@Delete" spring-ai-backend/src/main/java`
- `rg -n "APIRouter|FastAPI|router" python-ai-backend/app`
- `rg -n "\\.test\\.|\\.spec\\.|__tests__|src/test|tests" .`
