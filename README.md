# Liqi Tools Skill

一个基于 [利器](https://liqi.io/) 创作者访谈的来源可追溯工具推荐 Skill。

它把 251 篇创作者访谈保存为 Markdown，并提供本地 SQLite 检索库。用户可以按任务和场景查询工具，例如视频剪辑、写作、设计、编程、知识管理和团队协作；回答应附创作者、访谈链接和简短证据。

## 当前状态

- 251 篇创作者访谈 Markdown
- 251 个创作者档案
- 848 个 Workflow / Case
- 2,983 个跨创作者工具聚合
- 848 个工具相关段落
- 2,983 个机器抽取实体
- 7,712 条机器抽取提及
- 两批共 40 条人工校准记录
- 6 个完整人工校准 Workflow / Case
- 完整人工校准 Workflow / Case 会优先于机器生成案例展示
- 所有未校准实体均保留 `provisional` 状态

## 安装

### Codex

将 `liqi-tools/` 目录复制到 `~/.codex/skills/liqi-tools/`。Codex 使用 `SKILL.md`，并可读取 `agents/openai.yaml` 作为界面元数据。

### Claude Code

将同一个 `liqi-tools/` 目录复制到 `~/.claude/skills/liqi-tools/`。Claude Code 使用同一个 `SKILL.md` 和目录内的脚本、数据库与参考资料。

两者共享核心 `SKILL.md`；平台差异只存在于可选的界面元数据和安装目录。

首次使用时，Skill 只会补问任务、平台和关键限制中缺失的部分；需求已经明确时会直接检索，并先返回最多三个带来源的候选。详细交互规范见 `liqi-tools/references/onboarding.md`。

Skill 提供三个入口：按任务快速找工具、按 Workflow / Case 学习创作者如何完成工作、按工具聚合不同创作者的使用场景与评价。访谈链接直接附在结果中。

## 维护与校准

需要 Python 3。发布前运行：

```bash
make release-check
```

它会重建档案层和数据库、同步 Skill 数据包、执行数据验证、执行 8 个真实问题评测，并检查 Skill 格式。工具实体按 `data/review-queue.jsonl` 分批复核，人工确认结果写入 `data/reviewed-tools.jsonl`；完整工作流案例写入 `data/reviewed-workflow-cases.jsonl`。

发布版本同时包含 `reviewed` 与 `provisional` 数据。前者已经核对创作者、场景、证据和推荐强度；后者只能作为发现线索，不能被表述为确定推荐。访谈属于历史资料，当前价格、版本、可用性和安全性需要另行验证。

## 版权与使用边界

利器页面声明 CC-BY-NC-SA。发布和使用时保留来源、署名、原始链接，不将语料用于模型训练或微调，也不在回答中复制整篇访谈或长段落。工具当前是否仍可用需要另行联网核实，不能从历史访谈推断。
