---
name: code-review
description: 用于当前项目的 Claude 代码审查与评分。适用于“代码审查、PR/MR review、质量评分、风险评估”等任务，按 v2.0 规范输出 P0/P1/P2、总分、星级和合并结论，并将结果写入根目录 code-review 文件夹。
---

# Claude 代码审查技能 v2

执行审查时遵循以下规则：

## 审查流程

1. 先读取 `references/review-standard-v2.md` 作为评分与分级标准。
2. 读取 `references/project-review-focus.md`，锁定本项目关键风险点。
3. 通过 `git branch --show-current` 获取当前分支名，并将分支名中的 `/` 替换为 `-`，生成报告文件名，例如 `feat/harness-engineering` -> `feat-harness-engineering.md`。
4. 将最终审查结果写入仓库根目录 `code-review/` 文件夹，文件路径固定为 `code-review/{sanitized-branch-name}.md`。
5. 结合代码与命令结果形成证据链（文件/行号）。
6. 问题分组输出顺序固定：
   - `P0（🔴严重）`
   - `P1（🟡中等）`
   - `P2（🟢轻微）`
7. 每个问题说明：
   - 为什么是问题
   - 在哪里出现
   - 应该怎么改
8. 严重等级与优先级映射固定为：
   - `P0 = 🔴严重`
   - `P1 = 🟡中等`
   - `P2 = 🟢轻微`
9. 根据扣分规则计算分数并映射星级。
10. 用标准模板给出最终总结，并确保“终端输出内容”和“写入 md 文件内容”一致。

## 输出约束

- Findings 必须在前，评分与结论在后。
- 必须给出准确路径和行号。
- 必须给出 `P0 / P1 / P2` 三类问题计数。
- 必须在报告中写明当前分支名、报告文件路径和最终评分。
- 必须将最终审查结果落盘到 `code-review/{sanitized-branch-name}.md`。
- 若 `code-review/` 不存在，应先创建后再写入报告。
- 对暂不修复的中等问题，要求记录技术债。
- 若未发现问题，也要写明剩余风险和测试缺口。

## 建议输出结构

```markdown
# Code Review - {branch-name}

- Branch: `{branch-name}`
- Report: `code-review/{sanitized-branch-name}.md`
- Score: `85/100`
- Stars: `⭐⭐⭐⭐`
- Decision: `Approve with suggestions`

## P0（🔴严重）
1. [path:line] 问题说明

## P1（🟡中等）
1. [path:line] 问题说明

## P2（🟢轻微）
1. [path:line] 问题说明

## Summary
- P0: 0
- P1: 2
- P2: 3
```
