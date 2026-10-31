# Thesis Writing Style

帮助撰写中文理工科学位论文（硕士/博士）**写作语言与框架**的 Claude Code / Codex skill。

它关心“写成什么样”：章引言怎么开头、章小结怎么收尾、公式怎么引出和解释、表格结果怎么分析、结论展望怎么写。排版和 LaTeX 格式请配合所在学校的论文模板使用。

## 包含什么

- **共识规则**：默认照做的写法，例如章小结用完成时、不引出下一章。
- **分歧变体**：存在多种常见做法的地方，附推荐选项。
- **句式模板**：可直接套用的通用句式。
- **反例清单**：应当避免的写法。

## 文件结构

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 入口：共识规则、分歧点、自查清单 |
| `references/01_global_structure.md` | 章节规划、章名节名、章间逻辑、篇幅 |
| `references/02_abstract.md` | 摘要与关键词 |
| `references/03_introduction_chapter.md` | 绪论 |
| `references/04_chapter_opening.md` | 章引言 |
| `references/05_chapter_summary.md` | 本章小结 |
| `references/06_method_and_equations.md` | 方法叙述与公式 |
| `references/07_figures_tables_results.md` | 图表与结果分析 |
| `references/08_experiments_and_deployment.md` | 实验、消融、实物/边缘部署 |
| `references/09_language_style.md` | 人称、衔接词、反例 |
| `references/10_conclusion_outlook.md` | 结论与展望 |
| `references/11_theory_and_optimization.md` | 定理证明、优化求解、复杂度与收敛性 |
| `references/sources.md` | 各类论文写法特点 |

## 安装

把 `thesis-writing-style` 文件夹复制到：

- Claude Code：`~/.claude/skills/`
- Codex：`~/.codex/skills/`

## 使用

```text
按 thesis-writing-style 帮我写第三章的章引言。
用 thesis-writing-style 检查这一章的小结和表格分析写法。
```

你自己或导师的写作偏好优先于 skill 中的建议。
