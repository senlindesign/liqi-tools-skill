#!/usr/bin/env python3
"""Search provisional Liqi entities and return source-backed interview hits."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def search_workflows(connection: sqlite3.Connection, tokens: list[str], limit: int, as_json: bool) -> None:
    connection.row_factory = sqlite3.Row
    reviewed_rows = connection.execute("SELECT * FROM reviewed_workflow_cases ORDER BY id").fetchall()
    rows = connection.execute("SELECT * FROM workflow_cases ORDER BY id").fetchall()
    results = []
    for row in reviewed_rows:
        stages = json.loads(row["stages_json"])
        principles = json.loads(row["principles_json"])
        limitations = json.loads(row["limitations_json"])
        tools = []
        for stage in stages:
            for tool in stage.get("tools", []):
                if tool not in tools:
                    tools.append(tool)
        haystack = " ".join([row["task"], row["creator"], row["role"], row["evidence"], *principles, *limitations, *tools]).casefold()
        if not all(token in haystack for token in tokens):
            continue
        score = 40 + sum(16 if token in row["task"].casefold() else 5 for token in tokens)
        results.append({"score": score, "creator": row["creator"], "role": row["role"], "title": row["task"], "stage": "完整工作流", "tools": tools, "evidence": row["evidence"], "principles": principles, "limitations": limitations, "source_url": row["source_url"], "review_status": row["review_status"]})
    for row in rows:
        haystack = " ".join(str(row[key] or "") for key in ("creator", "role", "title", "stage", "tools_json", "evidence")).casefold()
        if not all(token in haystack for token in tokens):
            continue
        score = sum(12 if token in row["title"].casefold() or token in row["stage"].casefold() else 4 for token in tokens)
        results.append({"score": score, "creator": row["creator"], "role": row["role"], "title": row["title"], "stage": row["stage"], "tools": json.loads(row["tools_json"]), "evidence": row["evidence"], "principles": [], "limitations": [], "source_url": row["source_url"], "review_status": row["review_status"]})
    results.sort(key=lambda row: (-row["score"], row["creator"].casefold()))
    results = results[:limit]
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for row in results:
            print(f"{row['creator']}｜{row['role']} · {row['stage']} · {row['title']} · {row['review_status']}")
            print(f"  工具：{', '.join(row['tools'][:12])}")
            print(f"  来源：{row['source_url']}")
            print(f"  证据：{row['evidence']}")
            if row["principles"]:
                print(f"  原则：{'；'.join(row['principles'])}")
            if row["limitations"]:
                print(f"  限制：{'；'.join(row['limitations'])}")


def search_tool_aggregates(connection: sqlite3.Connection, tokens: list[str], limit: int, as_json: bool) -> None:
    connection.row_factory = sqlite3.Row
    creator_rows = connection.execute("SELECT id, name, role, source_url FROM creator_profiles").fetchall()
    creators_by_id = {row["id"]: dict(row) for row in creator_rows}
    rows = connection.execute("SELECT * FROM tool_aggregates").fetchall()
    results = []
    for row in rows:
        haystack = " ".join(str(row[key] or "") for key in ("name", "kind", "use_cases_json", "recommendation_strengths_json")).casefold()
        if not all(token in haystack for token in tokens):
            continue
        score = sum(14 if token in row["name"].casefold() else 5 for token in tokens) + 2 * row["reviewed_count"] + 0.2 * row["creator_count"]
        creator_ids = json.loads(row["creator_ids_json"])
        results.append({"score": round(score, 3), "entity_id": row["entity_id"], "name": row["name"], "kind": row["kind"], "creator_count": row["creator_count"], "mention_count": row["mention_count"], "reviewed_count": row["reviewed_count"], "recommendation_strengths": json.loads(row["recommendation_strengths_json"]), "use_cases": json.loads(row["use_cases_json"]), "creators": [creators_by_id[creator_id] for creator_id in creator_ids[:12] if creator_id in creators_by_id], "source_urls": json.loads(row["source_urls_json"]), "review_status": row["review_status"]})
    results.sort(key=lambda row: (-row["score"], row["name"].casefold()))
    results = results[:limit]
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for row in results:
            print(f"{row['name']} [{row['kind']}] · {row['creator_count']} creators · {row['mention_count']} mentions · reviewed: {row['reviewed_count']}")
            if row["use_cases"]:
                print(f"  场景：{'；'.join(row['use_cases'])}")
            if row["recommendation_strengths"]:
                print(f"  评价类型：{row['recommendation_strengths']}")
            if row["creators"]:
                print("  创作者：" + "；".join(f"{creator['name']}（{creator['role']}）" for creator in row["creators"][:6]))
            print(f"  来源：{' '.join(row['source_urls'][:5])}")


def search_creators(connection: sqlite3.Connection, tokens: list[str], limit: int, as_json: bool) -> None:
    connection.row_factory = sqlite3.Row
    rows = connection.execute("SELECT * FROM creator_profiles ORDER BY name COLLATE NOCASE").fetchall()
    results = []
    for row in rows:
        haystack = " ".join(str(row[key] or "") for key in ("name", "role", "title", "tags_json", "stages_json", "tool_names_json", "focus_areas_json")).casefold()
        if not all(token in haystack for token in tokens):
            continue
        score = sum(14 if token in row["name"].casefold() or token in row["role"].casefold() else 5 for token in tokens)
        results.append({"score": score, "creator_id": row["id"], "name": row["name"], "role": row["role"], "title": row["title"], "source_url": row["source_url"], "stages": json.loads(row["stages_json"]), "tool_names": json.loads(row["tool_names_json"])[:20], "focus_areas": json.loads(row["focus_areas_json"]), "workflow_count": row["workflow_count"], "review_status": row["review_status"]})
    results.sort(key=lambda row: (-row["score"], row["name"].casefold()))
    results = results[:limit]
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for row in results:
            print(f"{row['name']}｜{row['role']} · {row['workflow_count']} cases · {row['review_status']}")
            print(f"  阶段：{'、'.join(row['stages'])}")
            print(f"  工具：{'、'.join(row['tool_names'])}")
            print(f"  访谈：{row['source_url']}")


def excerpt(text: str, tokens: list[str], limit: int = 220) -> str:
    folded = text.casefold()
    positions = [folded.find(token) for token in tokens if folded.find(token) >= 0]
    start = max(0, min(positions) - 70) if positions else 0
    value = " ".join(text[start : start + limit].split())
    return ("…" if start else "") + value + ("…" if start + limit < len(text) else "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-resources", action="store_true")
    parser.add_argument("--mode", choices=["task", "workflow", "tool", "creator"], default="task")
    parser.add_argument("--kind", choices=["software", "hardware", "recommended_resource", "information_source"])
    options = parser.parse_args()
    tokens = [token.casefold() for token in options.query.split() if token.strip()]
    if not tokens:
        raise SystemExit("query must not be empty")

    connection = sqlite3.connect(ROOT / "data/liqi-tools.sqlite3")
    connection.row_factory = sqlite3.Row
    if options.mode == "workflow":
        search_workflows(connection, tokens, options.limit, options.json)
        return
    if options.mode == "tool":
        search_tool_aggregates(connection, tokens, options.limit, options.json)
        return
    if options.mode == "creator":
        search_creators(connection, tokens, options.limit, options.json)
        return
    reviewed_rows = connection.execute(
        "SELECT * FROM reviewed_mentions WHERE review_status = 'reviewed'"
    ).fetchall()
    reviewed_by_entity = defaultdict(list)
    for row in reviewed_rows:
        reviewed_by_entity[row["entity_id"]].append(row)
    rows = connection.execute(
        """
        SELECT e.id, e.name, e.kind, e.interview_count, e.review_status,
               group_concat(DISTINCT a.alias) AS aliases,
               m.name_raw, m.source_kind, m.heading, m.context, m.source_url,
               i.title AS interview_title
        FROM mentions m
        JOIN entities e ON e.id = m.entity_id
        JOIN interviews i ON i.id = m.interview_id
        LEFT JOIN aliases a ON a.entity_id = e.id
        GROUP BY m.id
        """
    ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        if not options.include_resources and row["kind"] in {
            "media_resource", "article_resource", "document_resource", "information_source"
        }:
            continue
        if options.kind and row["kind"] != options.kind:
            continue
        haystack = " ".join(
            str(row[key] or "")
            for key in ("name", "aliases", "kind", "heading", "context", "interview_title")
        ).casefold()
        if not all(token in haystack for token in tokens):
            continue
        name_blob = f"{row['name']} {row['aliases'] or ''}".casefold()
        heading = row["heading"].casefold()
        context = row["context"].casefold()
        name_position = context.find(row["name"].casefold())
        token_scores = []
        for token in tokens:
            if token in name_blob:
                token_scores.append(12.0)
            elif token in heading:
                token_scores.append(5.0)
            else:
                token_position = context.find(token)
                distance = abs(token_position - name_position) if name_position >= 0 and token_position >= 0 else 240
                token_scores.append(6.0 / (1.0 + distance / 60.0))
        score = sum(token_scores) + 0.25 * math.log1p(row["interview_count"])
        reviewed_relevance = sum(
            1
            for reviewed in reviewed_by_entity.get(row["id"], [])
            if any(
                token in " ".join(
                    str(reviewed[key] or "")
                    for key in ("use_case", "evidence", "recommendation_strength")
                ).casefold()
                for token in tokens
            )
        )
        score += 8.0 * reviewed_relevance
        grouped[row["id"]].append((score, row))

    results = []
    for entity_rows in grouped.values():
        entity_rows.sort(key=lambda item: item[0], reverse=True)
        best_score, best = entity_rows[0]
        sources = []
        seen_urls = set()
        for _, row in entity_rows:
            if row["source_url"] in seen_urls:
                continue
            seen_urls.add(row["source_url"])
            sources.append(
                {
                    "interview": row["interview_title"],
                    "heading": row["heading"],
                    "source_kind": row["source_kind"],
                    "source_url": row["source_url"],
                    "evidence": excerpt(row["context"], tokens),
                }
            )
            if len(sources) == 3:
                break
        results.append(
            {
                "entity_id": best["id"],
                "name": best["name"],
                "kind": best["kind"],
                "interview_count": best["interview_count"],
                "review_status": best["review_status"],
                "reviewed_count": len(reviewed_by_entity.get(best["id"], [])),
                "reviewed_sources": [
                    {
                        "creator": row["creator"],
                        "use_case": row["use_case"],
                        "recommendation_strength": row["recommendation_strength"],
                        "source_url": row["source_url"],
                        "evidence": row["evidence"],
                    }
                    for row in reviewed_by_entity.get(best["id"], [])[:3]
                ],
                "score": round(best_score, 3),
                "sources": sources,
            }
        )
    results.sort(key=lambda row: (-row["score"], -row["interview_count"], row["name"].casefold()))
    results = results[: options.limit]
    if options.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for row in results:
            print(f"{row['name']} [{row['kind']}] · {row['interview_count']} interviews · {row['review_status']} · reviewed records: {row['reviewed_count']}")
            for reviewed in row["reviewed_sources"]:
                print(f"  ✓ {reviewed['use_case']} · {reviewed['recommendation_strength']} · {reviewed['creator']}")
                print(f"    {reviewed['source_url']} · {reviewed['evidence']}")
            for source in row["sources"]:
                print(f"  - {source['interview']} | {source['heading']} | {source['source_url']}")
                print(f"    {source['evidence']}")


if __name__ == "__main__":
    main()
