# 利器 Skill

[![Codex](https://img.shields.io/badge/Codex-Agent%20Skill-111111?style=flat-square)](https://developers.openai.com/codex/skills)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Agent%20Skill-D97757?style=flat-square)](https://code.claude.com/docs/en/skills)
[![MIT License](https://img.shields.io/badge/License-MIT-2ea44f?style=flat-square)](LICENSE)
[![Validate Skill](https://img.shields.io/github/actions/workflow/status/senlindesign/liqi-tools-skill/validate.yml?branch=main&style=flat-square&label=Validation)](https://github.com/senlindesign/liqi-tools-skill/actions/workflows/validate.yml)
[![Version](https://img.shields.io/badge/version-0.2.0-4c6ef5?style=flat-square)](https://github.com/senlindesign/liqi-tools-skill/releases)

从「利器」创作者访谈出发，按任务、工作流或具体工具，寻找有出处、有个人经验的工具建议。

## 「利器」是什么

[利器](https://liqi.io/) 是一个采访创作者的内容项目。它邀请写作者、设计师、程序员、导演、研究者和其他创造者，分享自己工作时使用的工具，以及选择和使用这些工具的方式。

在利器的语境里，工具不只是一款软件或一件硬件。一本书、一个网站、一套工作方法，只要能帮助人完成创造，都可以成为「利器」。因此，一篇访谈真正留下来的，往往不只是一份工具清单，还有一个人怎样工作、怎样思考，以及工具在他的生活里处于什么位置。

如今，这些访谈主要以 archive 的形式留在互联网上，这个 Skill 希望让它们继续被阅读和使用。

## 为什么做这个 Skill

互联网上并不缺工具推荐，真正稀少的是工具与具体的人、具体的工作和具体的经历之间的联系。

利器的内容始终从创作者出发：先认识一个人正在做什么，再看他为什么选择某个工具、在什么情境下使用、哪些地方真正帮到了他。这个 Skill 把访谈整理成可检索的创作者档案、工作流案例和工具聚合，让这些经验可以用更灵活、更个性化的方式重新进入今天的创作过程。

它不会给工具做统一排名。它更关心：有没有一位与你处境相近的创作者，他曾怎样完成类似的工作；你是否会因为理解他的选择，而重新理解一件工具。

## 核心特色

- **从创作者开始**：推荐会说明谁在使用、他在做什么，以及这项经验来自哪篇访谈。
- **保留工作情境**：除了工具名，也会呈现它在写作、剪辑、播客、设计、开发或知识管理流程中的具体位置。
- **允许不同经验并存**：同一个工具可以被不同创作者用于不同目的，不把这些差异压成一个笼统结论。
- **极度 Personal**：结果刻意保留个人经验和个人偏好，希望你能先与某位创作者产生共鸣，再理解他所使用的工具。
- **来源可追溯**：每项推荐都尽量附上创作者、简短证据和原始利器访谈链接。

## 可以怎么用

| 入口 | 适合的问题 | 你会得到什么 |
|---|---|---|
| 按任务找工具 | 「我想在 Mac 上剪人物访谈，用什么工具？」 | 少量工具建议、适用场景、创作者经验和来源 |
| 按 Workflow / Case 找 | 「一个小团队怎么完成播客的选题、录制和发布？」 | 相似创作者、工作阶段、每一步使用的工具和方法 |
| 按工具聚合 | 「利器里的创作者都怎么用 Notion？」 | 不同创作者的使用场景、评价差异和对应访谈 |

你也可以直接描述平台、免费/开源、团队协作或离线使用等限制。信息足够时，Skill 会直接检索；只有一个偏好确实会改变结果时，它才补问。历史访谈没有可靠约束证据时，Skill 会明确说明，而不是猜测。

## 回答示例

### 从一项任务进入

> **你：** 我准备做一档远程谈话播客，想看看别人是怎么完成整套流程的。

Skill 会先找到做过相似事情的创作者，再整理他们的工作方式。例如，《比特新声》的郝海龙和有才会共同收集素材、提前准备提纲，远程录音时分别保存音轨，后期主要处理隐私信息和明显口误。他们在不同阶段使用过 Dropbox Paper、Audio Hijack、Skype、Logic Pro、GarageBand、TextExpander 等工具。

回答还会保留这段经验的适用边界，并附上[原始访谈](https://liqi.io/bitvoicefm/)，方便继续阅读创作者自己的表达。

### 从一个工具进入

> **你：** 利器里的创作者怎么用 Notion？

Skill 不会只回答「Notion 是笔记工具」。它会分别告诉你：hb 用它记录工作日志和日常写作；李兴宇所在的团队用它协作维护设计语言文档。两个用法来自不同工作环境，也会分别附上对应的[个人访谈](https://liqi.io/hb/)和[团队协作访谈](https://liqi.io/lixingyu/)。

## 安装

需要 Node.js。使用开源的 [skills CLI](https://github.com/vercel-labs/skills) 安装：

### Codex

```bash
npx skills add senlindesign/liqi-tools-skill --skill liqi-tools -g -a codex -y
```

### Claude Code

```bash
npx skills add senlindesign/liqi-tools-skill --skill liqi-tools -g -a claude-code -y
```

也可以同时安装到两个 Agent：

```bash
npx skills add senlindesign/liqi-tools-skill --skill liqi-tools -g -a codex -a claude-code -y
```

手动安装时，将仓库中的 `liqi-tools/` 复制到 `~/.codex/skills/liqi-tools/` 或 `~/.claude/skills/liqi-tools/`。两者使用同一个核心 `SKILL.md`；Codex 还会读取可选的 `agents/openai.yaml` 界面元数据。

安装后，可以直接这样提问：

```text
用利器帮我找几个适合长篇写作的工具，最好有创作者的具体用法。
找一个独立创作者制作人物视频的完整工作流。
不同创作者分别怎样使用 Notion？
我想在 Windows 上做播客，优先推荐学习成本低的方案。
```

## 数据说明

当前语料包含 251 篇创作者访谈 Markdown，并据此建立创作者档案、机器生成的工作流线索和跨创作者工具聚合。当前版本包含 40 条人工核对工具记录和 6 个完整人工核对 Workflow / Case；其余机器抽取结果只作为访谈线索。安装包保留运行时数据库、人工核对层和原始访谈，维护用的中间 JSONL 只留在仓库根目录，避免重复打包。

## 维护与校准

维护脚本需要 Python 3。发布前运行：

```bash
make release-check
```

它会重建档案层和数据库、同步 Skill 数据包、执行数据验证、运行真实问题评测，并检查 Skill 格式。工具实体按 `data/review-queue.jsonl` 分批复核，人工确认结果写入 `data/reviewed-tools.jsonl`；完整工作流案例写入 `data/reviewed-workflow-cases.jsonl`。检索评测同时检查正例、负例、排序、无结果、输出体积和执行时间，触发边界样例保存在 `data/trigger-eval-cases.jsonl`。

发布版本同时包含 `reviewed` 与 `provisional` 数据。前者已经核对创作者、场景、证据和推荐强度；后者不能被表述为确定推荐。访谈属于历史资料，工具当前的价格、版本、可用性和安全性需要另行验证。

## 使用边界与版权

本项目的代码与原创文档使用 [MIT License](LICENSE)。归档访谈及由访谈内容衍生的数据遵循利器网站声明的 CC-BY-NC-SA 条款；完整的范围划分见[语料许可与使用说明](CORPUS_LICENSE.md)。

使用与再发布时请保留「利器」署名、原始链接和许可信息。

本项目不使用利器语料训练或微调模型。Skill 仅在用户请求时检索相关访谈内容，并将其作为临时上下文生成回答。运行平台如何处理对话数据，由对应平台的服务条款和用户数据设置决定。

利器访谈记录的是创作者在特定时期的工具选择。涉及工具版本、价格和当前可用性的内容，请以最新官方信息为准。

感谢曾经参与利器的编辑、志愿者与受访创作者。这个项目只是尝试为这些已经存在的经验，增加一种新的阅读入口。
