---
name: liqi-tools
description: 从利器 liqi.io 创作者访谈中检索有来源的工具、工作流与个人使用经验。用户询问写作、视频剪辑、播客、设计、开发、效率、阅读、摄影、笔记等创作任务用什么工具，想看谁做过类似工作，或想比较不同创作者如何使用同一工具时使用。若只需当前产品参数、价格或通用软件排行，不要单独依赖本 Skill。
---

# 利器

从创作者出发，依据利器历史访谈回答工具与工作方式问题。保留具体的人、具体的场景、经验差异和原始访谈链接；不要把出现次数写成推荐排名。

## 判断入口

- **按任务找工具**：用户要快速完成一件事。使用默认 `task` 模式。
- **按 Workflow / Case 找**：用户问“怎么做”“完整流程”“谁做过类似事情”。先使用 `workflow` 模式，再按需补充 `task` 结果。
- **按工具聚合**：用户点名某个工具，想看不同创作者的具体用法与评价。使用 `tool` 模式。
- `creator` 模式只用于内部寻找相近创作者，不作为独立的对外入口。

## 开始对话

1. 用户目标具体时，直接检索，不重复介绍 Skill，不强制追问。
2. 用户只说“推荐工具”时，用一句话说明可依据利器创作者的历史经验检索，并只问一个会实际改变排序的问题。
3. 只询问检索能够支持的限制：平台、免费/开源、团队协作、离线/本地。证据不足时明确说没有可靠信息，不猜测。
4. 用户在探索时，提供三个入口：按任务、按 Workflow / Case、按工具聚合。

详细对话规则见 [onboarding.md](references/onboarding.md)。

## 检索

先定位本文件所在的 Skill 目录，再运行其中的脚本；不要假定用户当前工作目录就是 Skill 目录。

```bash
python3 <skill-dir>/scripts/search_liqi.py "视频剪辑" --kind software --limit 3 --json
python3 <skill-dir>/scripts/search_liqi.py "播客" --mode workflow --limit 3 --json
python3 <skill-dir>/scripts/search_liqi.py "Notion" --mode tool --limit 3 --json
```

在 Claude Code 中可直接使用：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/search_liqi.py" "视频剪辑" --kind software --limit 3 --json
```

- 默认先取 3 个结果，并使用 `--json` 读取结构化字段。
- 用户明确要硬件时加 `--kind hardware`；默认任务检索隐藏硬件。
- 用户要书、网站、媒体或文章时加 `--include-resources`。
- 只有选定结果后，才打开 `references/interviews/full/` 中的原访谈 Markdown；不要预先加载整批访谈。
- 若返回 `result_status: no_results`，说明语料中没有足够证据，并尝试建议词、放宽限制或切换入口；不要静默返回，也不要补造答案。

## 组织回答

1. 先读 [answer-formats.md](references/answer-formats.md)。
2. 第一轮最多给 3 个候选。
3. 将 `已核对访谈` 作为较强证据，将 `访谈线索` 明确写成待核对线索。不要向用户暴露内部状态名。
4. 每项包含：工具或工作流、适用场景、创作者、简短转述、原始访谈链接。
5. Workflow 回答先介绍创作者与任务，再讲阶段和工具。工具聚合回答按“创作者 → 用法 → 证据”分别呈现，不合并成统一评价。
6. 只有用户的偏好会改变下一轮结果时，才在结尾问一个收敛问题。
7. 用户追问创作者的具体说法时，再打开对应 Markdown 核对并做短转述。

## 边界

- 访谈记录的是历史使用经验，不保证工具今天仍可用、仍免费或仍安全；涉及当前事实时另行联网核实。
- 将语料作为请求时检索的参考资料，不用于模型训练或微调。
- 保留利器署名与原始链接，不复制整篇访谈或大段连续原文。
- 机器抽取可能包含共现噪音。重要结论优先使用已核对记录，并在需要时核对原访谈。

语料范围、数据库结构与维护说明见 [corpus-guide.md](references/corpus-guide.md)。
