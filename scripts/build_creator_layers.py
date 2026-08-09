#!/usr/bin/env python3
"""Build creator dossiers, workflow cases, and cross-creator tool aggregates."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_provisional_index import normalize_name
from site_common import write_text


ROOT = Path(__file__).resolve().parent.parent


def read_jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines()]


def compact(value: str, limit: int = 600) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def creator_parts(title: str) -> tuple[str, str]:
    value = re.sub(r"^(利器访谈：|利器访谈\s*[:：])", "", title).strip()
    if "，" in value:
        name, role = value.split("，", 1)
    elif "," in value:
        name, role = value.split(",", 1)
    else:
        name, role = value, ""
    return name.strip(), role.strip()


def stage_for_heading(heading: str, content: str) -> str:
    heading_text = heading.casefold()
    if any(keyword in heading_text for keyword in ("硬件", "装备", "设备")):
        return "设备与环境"
    text = f"{heading} {content}".casefold()
    rules = [
        ("创作与生产", ("写作", "剪辑", "设计", "开发", "编程", "绘画", "制作", "创作", "录音", "播客")),
        ("信息输入", ("信息源", "阅读", "书", "rss", "稍后", "收藏", "订阅", "新闻")),
        ("项目与协作", ("协作", "项目", "任务", "团队", "进度", "管理", "日程")),
        ("设备与环境", ("硬件", "设备", "电脑", "手机", "显示器", "键盘")),
        ("生活与辅助", ("生活", "健康", "运动", "音乐", "娱乐")),
    ]
    for stage, keywords in rules:
        if any(keyword.casefold() in text for keyword in keywords):
            return stage
    return "工作环境"


def main() -> None:
    manifest = [row for row in read_jsonl("interviews-manifest.jsonl") if row["collection_decision"] == "include"]
    sections = read_jsonl("tool-sections.jsonl")
    entities = read_jsonl("entities.provisional.jsonl")
    mentions = read_jsonl("tool-candidates.jsonl") + read_jsonl("unlinked-candidates.jsonl")
    reviewed = read_jsonl("reviewed-tools.jsonl") if (ROOT / "data/reviewed-tools.jsonl").exists() else []

    manifest_by_id = {row["id"]: row for row in manifest}
    sections_by_interview: dict[str, list[dict]] = defaultdict(list)
    for row in sections:
        sections_by_interview[row["source_interview_id"]].append(row)
    mentions_by_section: dict[str, list[dict]] = defaultdict(list)
    for row in mentions:
        section_id = row.get("candidate_id", row.get("mention_id", "")).rsplit("-candidate-", 1)[0].rsplit("-lexicon-", 1)[0]
        mentions_by_section[section_id].append(row)
    mentions_by_entity: dict[str, list[dict]] = defaultdict(list)
    for row in mentions:
        mentions_by_entity[row.get("entity_id", "")].append(row)
    reviewed_by_entity: dict[str, list[dict]] = defaultdict(list)
    for row in reviewed:
        reviewed_by_entity[normalize_name(row["entity_name"])].append(row)

    profiles = []
    cases = []
    for interview in manifest:
        creator_name, role = creator_parts(interview["title"])
        interview_sections = sections_by_interview[interview["id"]]
        profile_id = interview["id"]
        profile_tool_names = []
        profile_entity_ids = []
        profile_stages = []
        profile_case_ids = []
        for section_index, section in enumerate(interview_sections, 1):
            profile_case_ids.append(f"{interview['id']}-case-{section_index:02d}")
            stage = stage_for_heading(section["heading"], section["content"])
            if stage not in profile_stages:
                profile_stages.append(stage)
            for mention in mentions_by_section[section["section_id"]]:
                raw = mention.get("tool_name_raw", mention.get("tool_name_matched", ""))
                if raw and raw not in profile_tool_names:
                    profile_tool_names.append(raw)
                if mention.get("entity_id") and mention["entity_id"] not in profile_entity_ids:
                    profile_entity_ids.append(mention["entity_id"])
        profiles.append(
            {
                "creator_id": profile_id,
                "name": creator_name,
                "role": role,
                "title": interview["title"],
                "source_interview_id": interview["id"],
                "source_url": interview["source_url"],
                "published_at": interview["published_at"],
                "tags": interview["tags"],
                "article_type": interview["article_type"],
                "workflow_count": len(interview_sections),
                "case_ids": profile_case_ids,
                "stages": profile_stages,
                "tool_names": profile_tool_names[:80],
                "tool_entity_ids": profile_entity_ids[:80],
                "focus_areas": interview["tags"] or ([role] if role else []),
                "review_status": "machine_profile",
            }
        )
        for index, section in enumerate(interview_sections, 1):
            section_mentions = mentions_by_section[section["section_id"]]
            names = []
            entity_ids = []
            for mention in section_mentions:
                raw = mention.get("tool_name_raw", mention.get("tool_name_matched", ""))
                if raw and raw not in names:
                    names.append(raw)
                if mention.get("entity_id") and mention["entity_id"] not in entity_ids:
                    entity_ids.append(mention["entity_id"])
            cases.append(
                {
                    "case_id": f"{interview['id']}-case-{index:02d}",
                    "creator_id": profile_id,
                    "source_interview_id": interview["id"],
                    "creator": creator_name,
                    "role": role,
                    "title": section["heading"],
                    "stage": stage_for_heading(section["heading"], section["content"]),
                    "tools": names[:40],
                    "tool_entity_ids": entity_ids[:40],
                    "evidence": compact(section["content"]),
                    "source_url": section["source_url"],
                    "review_status": "machine_case",
                }
            )

    aggregates = []
    for entity in entities:
        entity_id = entity["entity_id"]
        entity_reviewed = reviewed_by_entity[normalize_name(entity["name"])]
        creator_ids = sorted({row.get("source_interview_id", "") for row in mentions_by_entity[entity_id] if row.get("source_interview_id")})
        use_cases = sorted({row["use_case"] for row in entity_reviewed})
        source_urls = sorted({row.get("source_url", "") for row in mentions_by_entity[entity_id] if row.get("source_url")})
        strengths = Counter(row["recommendation_strength"] for row in entity_reviewed)
        aggregates.append(
            {
                "entity_id": entity_id,
                "name": entity["name"],
                "kind": entity["provisional_kind"],
                "creator_count": len(creator_ids),
                "mention_count": len(mentions_by_entity[entity_id]),
                "reviewed_count": len(entity_reviewed),
                "recommendation_strengths": dict(strengths),
                "use_cases": use_cases,
                "creator_ids": creator_ids,
                "source_urls": source_urls[:20],
                "review_status": "reviewed_aggregate" if entity_reviewed else "provisional_aggregate",
            }
        )

    profiles.sort(key=lambda row: row["name"].casefold())
    cases.sort(key=lambda row: (row["creator"].casefold(), row["case_id"]))
    aggregates.sort(key=lambda row: (-row["reviewed_count"], -row["creator_count"], row["name"].casefold()))
    write_text(ROOT / "data/creator-profiles.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in profiles))
    write_text(ROOT / "data/workflow-cases.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in cases))
    write_text(ROOT / "data/tool-aggregates.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in aggregates))
    print(json.dumps({"creator_profiles": len(profiles), "workflow_cases": len(cases), "tool_aggregates": len(aggregates)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
