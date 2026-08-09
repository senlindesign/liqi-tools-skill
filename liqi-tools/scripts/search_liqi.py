#!/usr/bin/env python3
"""Search the bundled Liqi creator-interview corpus."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = SKILL_ROOT / "references/data/liqi-tools.sqlite3"
DEFAULT_EVIDENCE_CHARS = 200
RESOURCE_KINDS = {"media_resource", "article_resource", "document_resource", "information_source"}

INTENTS = {
    "video_editing": ("视频剪辑", "视频 剪辑", "视频制作", "影像制作", "剪辑", "剪片", "视频后期", "影视后期", "后期", "调色", "出片"),
    "podcast": ("播客", "podcast", "录音", "音频制作", "音频剪辑", "远程录音"),
    "writing": ("写作", "写稿", "撰稿", "长篇写作", "markdown", "草稿", "文字创作"),
    "design": ("设计", "界面设计", "产品设计", "交互设计", "视觉设计", "原型"),
    "development": ("编程", "开发", "写代码", "coding", "程序员", "工程师"),
    "passwords": ("密码管理", "密码 管理", "密码", "password"),
    "notes": ("笔记", "记笔记", "知识管理", "资料归档", "第二大脑"),
    "reading": ("阅读", "稍后阅读", "读书", "rss"),
    "photography": ("摄影", "照片", "修图", "图片处理", "照片调色"),
    "project_management": ("项目管理", "任务管理", "看板", "gtd"),
}

INTENT_PRIMARY = {
    "video_editing": ("视频剪辑", "视频制作", "影像制作", "剪辑", "剪片", "视频后期", "影视后期", "出片"),
    "podcast": ("播客", "podcast", "录音", "音频制作", "音频剪辑", "远程录音"),
}

CONSTRAINTS = {
    "platform": ("macos", "mac", "windows", "ios", "iphone", "ipad", "android", "web", "网页", "手机", "跨平台", "linux"),
    "cost": ("免费", "开源", "预算", "便宜", "付费"),
    "collaboration": ("协作", "团队", "多人", "共享"),
    "privacy": ("隐私", "离线", "本地", "私有"),
    "learning": ("易上手", "简单", "学习成本", "新手"),
}

STATUS_LABELS = {
    "reviewed": "已核对访谈",
    "reviewed_case": "已核对访谈",
    "provisional": "访谈线索",
    "machine_case": "访谈线索",
}


@dataclass(frozen=True)
class QuerySpec:
    raw: str
    folded: str
    core_terms: tuple[str, ...]
    intent: str | None
    constraints: tuple[str, ...]


def normalize_query(query: str, mode: str) -> QuerySpec:
    folded = " ".join(query.casefold().split())
    compact = re.sub(r"\s+", "", folded)
    constraints = tuple(
        term
        for terms in CONSTRAINTS.values()
        for term in terms
        if term in folded or term in compact
    )
    if mode in {"tool", "creator"}:
        return QuerySpec(query, folded, (folded,), None, constraints)
    for intent, terms in INTENTS.items():
        if any(term in folded or re.sub(r"\s+", "", term) in compact for term in terms):
            return QuerySpec(query, folded, tuple(dict.fromkeys(term.casefold() for term in terms)), intent, constraints)
    words = [word for word in re.split(r"[\s,，、/]+", folded) if word and word not in constraints]
    return QuerySpec(query, folded, tuple(words or [folded]), None, constraints)


def term_score(text: str, terms: tuple[str, ...]) -> float:
    folded = text.casefold()
    hits = [term for term in terms if term in folded]
    if not hits:
        return 0.0
    return max(3.0, min(16.0, max(len(term) for term in hits) * 3.0)) + min(4.0, len(hits) - 1)


def constraint_score(text: str, constraints: tuple[str, ...]) -> float:
    folded = text.casefold()
    return min(6.0, 2.0 * sum(term in folded for term in constraints))


def primary_terms(spec: QuerySpec) -> tuple[str, ...]:
    return INTENT_PRIMARY.get(spec.intent or "", spec.core_terms)


def nearby_term_score(text: str, names: str, terms: tuple[str, ...], max_distance: int = 120) -> float:
    folded = text.casefold()
    name_terms = [value for value in re.split(r"[,，\s]+", names.casefold()) if len(value) > 1]
    name_positions = [folded.find(value) for value in name_terms if folded.find(value) >= 0]
    term_positions = [folded.find(term) for term in terms if folded.find(term) >= 0]
    if not term_positions:
        return 0.0
    if any(term in names.casefold() for term in terms):
        return term_score(names, terms)
    if not name_positions or min(abs(left - right) for left in name_positions for right in term_positions) > max_distance:
        return 0.0
    return term_score(text, terms)


def coherent_context_score(text: str, names: str, task_terms: tuple[str, ...], constraints: tuple[str, ...]) -> float:
    folded = text.casefold()
    name_terms = [value for value in re.split(r"[,，\s]+", names.casefold()) if len(value) > 1]
    positions = []
    for name in name_terms:
        start = 0
        while True:
            position = folded.find(name, start)
            if position < 0:
                break
            positions.append(position)
            start = position + len(name)
    for position in positions:
        window = folded[max(0, position - 100) : position + 130]
        if not any(term in window for term in task_terms):
            continue
        if constraints and not all(term in window for term in constraints):
            continue
        return term_score(window, task_terms)
    return 0.0


def clean_evidence(text: str, terms: tuple[str, ...], limit: int = DEFAULT_EVIDENCE_CHARS) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text or "")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.split(r"(?:责任编辑|编辑：|题图来自|本文由|©|Copyright)", text, maxsplit=1)[0]
    text = re.sub(r"\s+", " ", text).strip()
    folded = text.casefold()
    positions = [folded.find(term) for term in terms if folded.find(term) >= 0]
    start = max(0, min(positions) - 65) if positions else 0
    value = text[start : start + limit].strip()
    return ("…" if start else "") + value + ("…" if start + limit < len(text) else "")


def status_label(status: str, reviewed_count: int = 0) -> str:
    if reviewed_count:
        return STATUS_LABELS["reviewed"]
    return STATUS_LABELS.get(status, "访谈线索")


def emit(results: list[dict], spec: QuerySpec, as_json: bool, elapsed_ms: int, printer) -> None:
    if as_json:
        message = None if results else "没有找到足够相关的访谈证据；请换一个任务说法、减少限制，或改用 workflow / tool 模式。"
        print(json.dumps({
            "query": spec.raw,
            "intent": spec.intent,
            "constraints": list(spec.constraints),
            "result_status": "ok" if results else "no_results",
            "message": message,
            "suggested_queries": list(spec.core_terms[:4]) if not results else [],
            "elapsed_ms": elapsed_ms,
            "results": results,
        }, ensure_ascii=False, indent=2))
        return
    if not results:
        print("没有找到足够相关的访谈证据。可以换一种任务说法、减少限制，或改用 workflow / tool 模式。")
        if spec.core_terms:
            print("可尝试：" + "、".join(spec.core_terms[:4]))
        return
    for row in results:
        printer(row)


def search_workflows(connection: sqlite3.Connection, spec: QuerySpec, limit: int) -> list[dict]:
    results = []
    rows = connection.execute("SELECT * FROM reviewed_workflow_cases ORDER BY id").fetchall()
    for row in rows:
        stages = json.loads(row["stages_json"])
        principles = json.loads(row["principles_json"])
        limitations = json.loads(row["limitations_json"])
        tools = list(dict.fromkeys(tool for stage in stages for tool in stage.get("tools", [])))
        task_score = term_score(row["task"], spec.core_terms)
        if not task_score:
            continue
        related_intents = sum(any(term in row["task"].casefold() for term in terms) for terms in INTENTS.values())
        specificity = 12.0 / max(1, related_intents)
        score = 60 + task_score * 2 + specificity + constraint_score(" ".join([row["task"], row["evidence"], *tools]), spec.constraints)
        results.append({
            "score": round(score, 3), "creator": row["creator"], "role": row["role"], "task": row["task"],
            "stage": "完整工作流", "tools": tools, "evidence": clean_evidence(row["evidence"], spec.core_terms),
            "principles": principles[:2], "limitations": limitations[:2], "source_url": row["source_url"],
            "result_status": "已核对访谈", "record_status": row["review_status"],
        })
    rows = connection.execute("SELECT * FROM workflow_cases ORDER BY id").fetchall()
    for row in rows:
        task_text = " ".join(str(row[key] or "") for key in ("title", "stage", "evidence"))
        task_score = term_score(task_text, spec.core_terms)
        if not task_score:
            continue
        results.append({
            "score": round(10 + task_score + constraint_score(task_text, spec.constraints), 3),
            "creator": row["creator"], "role": row["role"], "task": row["title"], "stage": row["stage"],
            "tools": json.loads(row["tools_json"])[:12], "evidence": clean_evidence(row["evidence"], spec.core_terms),
            "principles": [], "limitations": [], "source_url": row["source_url"],
            "result_status": "访谈线索", "record_status": row["review_status"],
        })
    results.sort(key=lambda row: (-row["score"], row["creator"].casefold()))
    return results[:limit]


def creator_mentions(connection: sqlite3.Connection, entity_id: str, terms: tuple[str, ...]) -> list[dict]:
    reviewed = connection.execute(
        "SELECT creator, use_case, recommendation_strength, source_url, evidence FROM reviewed_mentions WHERE entity_id = ? ORDER BY creator",
        (entity_id,),
    ).fetchall()
    results = [{
        "creator": row["creator"], "use_case": row["use_case"], "recommendation_strength": row["recommendation_strength"],
        "source_url": row["source_url"], "evidence": clean_evidence(row["evidence"], terms), "result_status": "已核对访谈",
    } for row in reviewed]
    seen = {row["source_url"] for row in results}
    provisional = connection.execute(
        """
        SELECT i.title AS creator, m.heading, m.context, m.source_url
        FROM mentions m JOIN interviews i ON i.id = m.interview_id
        WHERE m.entity_id = ? ORDER BY i.published_at DESC
        """, (entity_id,),
    ).fetchall()
    for row in provisional:
        if row["source_url"] in seen:
            continue
        results.append({
            "creator": row["creator"], "use_case": row["heading"], "recommendation_strength": "contextual_mention",
            "source_url": row["source_url"], "evidence": clean_evidence(row["context"], terms), "result_status": "访谈线索",
        })
        seen.add(row["source_url"])
        if len(results) >= 8:
            break
    return results


def search_tool_aggregates(connection: sqlite3.Connection, spec: QuerySpec, limit: int) -> list[dict]:
    results = []
    for row in connection.execute("SELECT * FROM tool_aggregates"):
        aliases = connection.execute("SELECT alias FROM aliases WHERE entity_id = ?", (row["entity_id"],)).fetchall()
        names = " ".join([row["name"], *(alias["alias"] for alias in aliases)]).casefold()
        if not all(term in names for term in spec.core_terms):
            continue
        mappings = creator_mentions(connection, row["entity_id"], spec.core_terms)
        score = 40 + 20 * all(term in row["name"].casefold() for term in spec.core_terms) + 3 * row["reviewed_count"] + math.log1p(row["creator_count"])
        results.append({
            "score": round(score, 3), "entity_id": row["entity_id"], "name": row["name"], "kind": row["kind"],
            "creator_count": row["creator_count"], "mention_count": row["mention_count"], "reviewed_count": row["reviewed_count"],
            "use_cases": json.loads(row["use_cases_json"]), "creator_mentions": mappings,
            "result_status": status_label(row["review_status"], row["reviewed_count"]), "record_status": row["review_status"],
        })
    results.sort(key=lambda row: (-row["score"], row["name"].casefold()))
    return results[:limit]


def search_creators(connection: sqlite3.Connection, spec: QuerySpec, limit: int) -> list[dict]:
    results = []
    for row in connection.execute("SELECT * FROM creator_profiles ORDER BY name COLLATE NOCASE"):
        haystack = " ".join(str(row[key] or "") for key in ("name", "role", "title", "tags_json", "stages_json", "tool_names_json", "focus_areas_json"))
        score = term_score(haystack, spec.core_terms)
        if not score:
            continue
        results.append({
            "score": round(score, 3), "creator_id": row["id"], "name": row["name"], "role": row["role"],
            "source_url": row["source_url"], "stages": json.loads(row["stages_json"]),
            "tool_names": json.loads(row["tool_names_json"])[:16], "focus_areas": json.loads(row["focus_areas_json"]),
            "workflow_count": row["workflow_count"], "result_status": "访谈线索", "record_status": row["review_status"],
        })
    results.sort(key=lambda row: (-row["score"], row["name"].casefold()))
    return results[:limit]


def search_tasks(connection: sqlite3.Connection, spec: QuerySpec, limit: int, kind: str | None, include_resources: bool) -> list[dict]:
    reviewed_by_entity = defaultdict(list)
    for row in connection.execute("SELECT * FROM reviewed_mentions WHERE review_status = 'reviewed'"):
        reviewed_by_entity[row["entity_id"]].append(row)
    rows = connection.execute("""
        SELECT e.id, e.name, e.kind, e.interview_count, e.review_status,
               group_concat(DISTINCT a.alias) AS aliases, m.heading, m.context, m.source_url,
               i.title AS interview_title
        FROM mentions m JOIN entities e ON e.id = m.entity_id JOIN interviews i ON i.id = m.interview_id
        LEFT JOIN aliases a ON a.entity_id = e.id GROUP BY m.id
    """).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        if kind and row["kind"] != kind:
            continue
        if not kind and row["kind"] == "hardware":
            continue
        if not include_resources and row["kind"] in RESOURCE_KINDS:
            continue
        reviewed = reviewed_by_entity.get(row["id"], [])
        relevance_terms = primary_terms(spec)
        direct_reviews = [(item, term_score(item["use_case"], relevance_terms)) for item in reviewed]
        direct_reviews = [(item, score) for item, score in direct_reviews if score]
        context_blob = " ".join([row["heading"] or "", row["context"] or ""])
        entity_names = f"{row['name']} {row['aliases'] or ''}"
        contextual = coherent_context_score(context_blob, entity_names, relevance_terms, spec.constraints)
        review_constraint_match = any(
            all(term in f"{item['use_case']} {item['evidence']}".casefold() for term in spec.constraints)
            for item, _ in direct_reviews
        ) if spec.constraints else True
        if spec.constraints and not review_constraint_match:
            continue
        if not direct_reviews and not contextual:
            continue
        score = contextual + term_score(entity_names, relevance_terms) + constraint_score(context_blob, spec.constraints)
        if direct_reviews:
            score += 35 + max(review_score for _, review_score in direct_reviews) * 2
            score += 3 * len(direct_reviews)
            if any(item["recommendation_strength"] == "explicit_recommendation" for item, _ in direct_reviews):
                score += 8
        score += 0.3 * math.log1p(row["interview_count"])
        grouped[row["id"]].append((score, row, direct_reviews))

    results = []
    for entity_rows in grouped.values():
        entity_rows.sort(key=lambda item: item[0], reverse=True)
        best_score, best, _ = entity_rows[0]
        relevant_reviews = []
        for review in reviewed_by_entity.get(best["id"], []):
            if term_score(review["use_case"], primary_terms(spec)):
                relevant_reviews.append({
                    "creator": review["creator"], "use_case": review["use_case"],
                    "recommendation_strength": review["recommendation_strength"], "source_url": review["source_url"],
                    "evidence": clean_evidence(review["evidence"], spec.core_terms), "result_status": "已核对访谈",
                })
        sources, seen = [], set()
        if not relevant_reviews:
            for _, row, _ in entity_rows:
                if row["source_url"] in seen:
                    continue
                seen.add(row["source_url"])
                sources.append({
                    "creator": row["interview_title"], "heading": row["heading"], "source_url": row["source_url"],
                    "evidence": clean_evidence(row["context"], spec.core_terms), "result_status": "访谈线索",
                })
                if len(sources) == 2:
                    break
        results.append({
            "entity_id": best["id"], "name": best["name"], "kind": best["kind"], "interview_count": best["interview_count"],
            "result_status": status_label(best["review_status"], len(relevant_reviews)), "record_status": best["review_status"],
            "reviewed_count": len(relevant_reviews), "reviewed_sources": relevant_reviews[:3], "score": round(best_score, 3), "sources": sources,
        })
    results.sort(key=lambda row: (-row["score"], -row["reviewed_count"], -row["interview_count"], row["name"].casefold()))
    return results[:limit]


def print_workflow(row: dict) -> None:
    print(f"{row['creator']}｜{row['role']} · {row['task']} · {row['result_status']}")
    print(f"  工具：{', '.join(row['tools'][:10])}")
    print(f"  来源：{row['source_url']}")
    print(f"  证据：{row['evidence']}")


def print_tool(row: dict) -> None:
    print(f"{row['name']} [{row['kind']}] · {row['creator_count']} 位创作者 · {row['result_status']}")
    for mention in row["creator_mentions"][:5]:
        print(f"  - {mention['creator']}｜{mention['use_case']} · {mention['result_status']}")
        print(f"    {mention['source_url']} · {mention['evidence']}")


def print_creator(row: dict) -> None:
    print(f"{row['name']}｜{row['role']} · {row['workflow_count']} 个案例 · {row['result_status']}")
    print(f"  工具：{'、'.join(row['tool_names'])}")
    print(f"  访谈：{row['source_url']}")


def print_task(row: dict) -> None:
    print(f"{row['name']} [{row['kind']}] · {row['result_status']}")
    for item in row["reviewed_sources"]:
        print(f"  - {item['creator']}｜{item['use_case']} · {item['result_status']}")
        print(f"    {item['source_url']} · {item['evidence']}")
    if not row["reviewed_sources"] and row["sources"]:
        item = row["sources"][0]
        print(f"  - {item['creator']}｜{item['heading']} · {item['result_status']}")
        print(f"    {item['source_url']} · {item['evidence']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-resources", action="store_true")
    parser.add_argument("--mode", choices=["task", "workflow", "tool", "creator"], default="task")
    parser.add_argument("--kind", choices=["software", "hardware", "recommended_resource", "information_source"])
    options = parser.parse_args()
    if options.limit < 1:
        parser.error("--limit must be greater than zero")
    if not options.query.strip():
        parser.error("query must not be empty")
    if not DATABASE_PATH.exists():
        raise SystemExit(f"database not found: {DATABASE_PATH}; reinstall the Skill or run make build")

    started = time.perf_counter()
    spec = normalize_query(options.query, options.mode)
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            if options.mode == "workflow":
                results, printer = search_workflows(connection, spec, options.limit), print_workflow
            elif options.mode == "tool":
                results, printer = search_tool_aggregates(connection, spec, options.limit), print_tool
            elif options.mode == "creator":
                results, printer = search_creators(connection, spec, options.limit), print_creator
            else:
                results = search_tasks(connection, spec, options.limit, options.kind, options.include_resources)
                printer = print_task
    except sqlite3.Error as exc:
        raise SystemExit(f"database error: {exc}") from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    emit(results, spec, options.json, elapsed_ms, printer)


if __name__ == "__main__":
    main()
