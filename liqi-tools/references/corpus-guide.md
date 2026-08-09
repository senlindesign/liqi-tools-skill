# Liqi Corpus Guide

This skill packages a local reference corpus extracted from `https://liqi.io/categories/interview/`.

## Scope

- Manifest rows: 254
- Included creator interviews: 251
- Excluded editorial/misclassified posts: 3
- Full Markdown interviews: 251
- Creator profiles: 251
- Tool-related sections: 848
- Workflow / Case records: 848
- Reviewed Workflow / Case records: 6
- Provisional entities: 2,983
- Cross-creator tool aggregates: 2,983
- Provisional mentions: 7,712
- Reviewed tool records: 40 (batches 1–2)

The corpus is designed for source-backed recommendations, not for claiming a complete or hand-reviewed knowledge base.

The bundled review queue contains one review task record for each provisional entity.

Only the reviewed records should be described as confirmed recommendations. All other entities remain provisional until their source context is checked.

## SQLite Schema

`references/data/liqi-tools.sqlite3` contains:

```sql
interviews(id, title, published_at, source_url, tags_json, article_type)
sections(id, interview_id, heading, content)
entities(id, name, kind, linked_mention_count, interview_count, review_status)
mentions(id, entity_id, section_id, interview_id, name_raw, source_kind, heading, context, source_url, review_status)
creator_profiles(id, name, role, title, interview_id, source_url, published_at, tags_json, article_type, workflow_count, case_ids_json, stages_json, tool_names_json, tool_entity_ids_json, focus_areas_json, review_status)
workflow_cases(id, creator_id, interview_id, creator, role, title, stage, tools_json, tool_entity_ids_json, evidence, source_url, review_status)
reviewed_workflow_cases(id, task, creator, role, interview_id, source_url, stages_json, principles_json, limitations_json, evidence, review_batch, review_status)
tool_aggregates(entity_id, name, kind, creator_count, mention_count, reviewed_count, recommendation_strengths_json, use_cases_json, creator_ids_json, source_urls_json, review_status)
aliases(entity_id, alias)
```

Useful entity kinds include `software`, `hardware`, `recommended_resource`, and `information_source`. Some extracted resources are classified as `media_resource`, `article_resource`, or `document_resource`; the search script hides these by default unless `--include-resources` is passed.

## Search Notes

`scripts/search_liqi.py` performs deterministic intent expansion, constraint separation, local evidence-window matching, and reviewed-evidence ranking over the SQLite data. It is a retrieval aid, not semantic proof.

Use `--mode workflow` to search creator-led cases and `--mode tool` to aggregate one tool across creators. Both modes are retrieval aids; important claims still require checking the original Markdown.

Recommended practice:

1. Start with the user's natural query. Common compact Chinese phrases such as `视频剪辑` and `密码管理` are normalized automatically.
2. Compare repeated entities and source excerpts.
3. Open the Markdown interview when the result depends on exact creator wording.
4. Present `已核对访谈` as stronger evidence and `访谈线索` as a lead. Internal status names remain machine-facing.

The distributable package contains the SQLite runtime database, reviewed tool/workflow records, and full interview Markdown. Maintenance-only JSONL layers remain in the repository root and are rebuilt before release.

## Evidence And Copyright

The archived pages indicate CC-BY-NC-SA. Use this material for reference and attribution. In user-facing answers:

- Include the original `liqi.io` interview URL when citing a creator mention.
- Prefer paraphrase and short snippets.
- Do not reproduce full interviews or long contiguous sections.
- Do not use the corpus as model-training data.

## Maintenance Notes

The current extraction is provisional and script-generated. If stronger product quality is needed, add a reviewed layer that stores:

- canonical tool name
- creator
- explicit use case
- recommendation strength
- quoted or paraphrased evidence
- source interview ID and URL
- reviewer status

The generated review queue is ordered by interview frequency and linked evidence. High-priority rows are useful starting points, but frequency alone does not prove recommendation strength.
