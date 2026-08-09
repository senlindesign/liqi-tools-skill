---
name: liqi-tools
description: Source-backed recommendations from the Liqi.io creator interview corpus. Use when a user asks for tools, apps, hardware, workflows, or resources recommended by creators in 利器/liqi.io interviews, especially for task-based recommendations such as writing, video editing, programming, design, productivity, reading, photography, note-taking, or creative work.
---

# Liqi Tools

This is an Agent Skills-compatible package. The core contract is this `SKILL.md`; Codex may additionally read `agents/openai.yaml` for UI metadata, while Claude Code discovers the same file when the directory is installed under `.claude/skills/liqi-tools/`.

Use this skill to recommend tools and resources from the archived 利器 interview corpus with source links and short evidence. The bundled corpus currently contains 251 creator profiles, 848 machine-generated workflow cases, 6 reviewed workflow cases, 2,983 cross-creator tool aggregates, 7,712 provisional mentions, and 40 reviewed tool records across two batches.

## Use-time onboarding

On the first invocation, give a one-sentence orientation: this Skill recommends tools mentioned by 利器 creators and links back to the original interviews. Then ask for the user's goal if it is not already clear.

Collect only the minimum missing context, preferably in one question:

- task or desired outcome
- platform or environment (for example macOS, Windows, iOS, Android, web)
- important constraints such as budget, privacy, collaboration, learning curve, or open source

If the request is already specific, skip the questions and search immediately. Do not make the user fill out a form. If the user is exploring, offer three entry points: recommend by task, browse by creator, or find the original interview.

For the first answer, return at most three strong candidates and label each as `已人工校准` or `机器初筛`. Include the fit, use scenario, creator, original interview link, and a short paraphrased evidence note. End with one refinement question, such as whether the user prioritizes price, platform, or workflow fit. Only expand the list after the user asks or after the constraints are clear.

Never imply that a creator's historical use guarantees current availability, pricing, security, or suitability. For those questions, say that the interview is historical and offer a separate current-web verification.

## Quick Start

Run the local search script first:

```bash
python3 scripts/search_liqi.py "视频 剪辑" --kind software --limit 8
python3 scripts/search_liqi.py "播客" --mode workflow --limit 5
python3 scripts/search_liqi.py "Notion" --mode tool --limit 3
python3 scripts/search_liqi.py "独立开发者" --mode creator --limit 5
python3 scripts/search_liqi.py "写作" --include-resources --limit 8
python3 scripts/search_liqi.py "密码 管理" --kind software --json
```

Use `--kind software` or `--kind hardware` when the user asks for tools. Use `--include-resources` when books, websites, media, or articles may be useful. Use `--json` when you need structured output for ranking, grouping, or further processing.

## Entry modes

Route the user's intent to one of three modes:

- **Task mode** (default): quick, short-list recommendations for a concrete task.
- **Workflow mode** (`--mode workflow`): creator-led cases showing who did similar work, which stages they used, and which tools appeared in each stage. Prefer `reviewed_case` results; only use `machine_case` as a clearly marked lead.
- **Tool mode** (`--mode tool`): one tool across creators, grouped by use case and reviewed recommendation strength. Attach source links directly to the aggregated answer; do not make the user request a separate trace mode.
- **Creator mode** (`--mode creator`): internal browsing of creator dossiers by role or focus area; use it to support workflow answers, not as a fourth user-facing promise.

When a task question implies a complete process, combine workflow mode first and task mode second: identify comparable creators and cases, then extract a short tool recommendation from them.

## Answering Workflow

1. Search with `scripts/search_liqi.py` using the user's task words and close synonyms.
2. Prefer results with direct task-context evidence, repeated interview appearances, and clear creator usage over generic co-mentions.
3. Open the relevant original Markdown file under `references/interviews/full/` when the evidence excerpt is ambiguous or when the user asks how the creator described the tool.
4. Return a compact recommendation list with: tool/resource name, why it fits, suitable scenario, creator/interview source, original liqi.io URL, and a short paraphrased evidence note.
5. State uncertainty when a result is only a provisional extraction or appears because of contextual co-mention.
6. In workflow mode, describe the creator and the work before naming tools. In tool mode, preserve differences between creators instead of averaging them into one verdict.
7. Read `references/answer-formats.md` before composing a user-facing recommendation, workflow, or cross-creator aggregation.

## Corpus Files

- `scripts/search_liqi.py`: search entities and mentions in the bundled SQLite database.
- `references/data/liqi-tools.sqlite3`: primary local database for search and custom SQL.
- `references/data/entities.provisional.jsonl`: provisional normalized entities.
- `references/data/review-queue.jsonl`: entity-level queue for human confirmation of names, recommendation status, use case, and evidence.
- `references/data/reviewed-tools.jsonl`: manually checked first-batch records with explicit use cases and recommendation strength.
- `references/data/creator-profiles.jsonl`: one dossier per included creator/interview, including stages, tool set, and case IDs.
- `references/data/workflow-cases.jsonl`: machine-derived cases grouped by creator and workflow stage.
- `references/data/reviewed-workflow-cases.jsonl`: manually checked complete cases with task, stages, principles, limitations, and source link.
- `references/data/tool-aggregates.jsonl`: cross-creator tool view with use cases, counts, and review state.
- `references/data/tool-sections.jsonl`: tool-related interview sections.
- `references/data/interviews-manifest.jsonl`: source URLs, dates, IDs, and inclusion decisions.
- `references/interviews/full/*.md`: full Markdown interview archives with frontmatter and original source URL.
- `references/corpus-guide.md`: schema, limitations, and licensing/use notes. Read it before custom SQL, corpus maintenance, or higher-stakes claims.
- `references/onboarding.md`: detailed first-use flow and output acceptance checks; read it when designing or evaluating the conversation experience.
- `references/answer-formats.md`: compact output contracts for task, workflow, and tool modes.

## Source And License Boundaries

Treat the corpus as reference material, not training data. The source site indicated CC-BY-NC-SA in the archived pages. Return summaries, short evidence snippets, and original links; do not reproduce full interviews or large contiguous passages.

The database is provisional. Entity normalization and mention extraction are automated, so verify important recommendations against the original Markdown and link before presenting them as strong claims. The review queue identifies what still needs confirmation; it is not a claim that every provisional entity is a recommendation.
