#!/usr/bin/env python3
"""Build a small, auditable queue for human review of provisional entities."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data/liqi-tools.sqlite3"
OUT_PATH = ROOT / "data/review-queue.jsonl"


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT e.id, e.name, e.kind, e.interview_count, e.linked_mention_count,
               e.review_status, COUNT(DISTINCT m.id) AS mention_count,
               COUNT(DISTINCT CASE WHEN m.source_kind = 'linked' THEN m.id END) AS linked_count,
               COUNT(DISTINCT CASE WHEN m.source_kind = 'lexicon_match' THEN m.id END) AS lexicon_count,
               MIN(m.source_url) AS example_source_url
        FROM entities e
        LEFT JOIN mentions m ON m.entity_id = e.id
        GROUP BY e.id
        ORDER BY e.interview_count DESC, linked_count DESC, e.name COLLATE NOCASE
        """
    ).fetchall()
    connection.close()

    OUT_PATH.write_text(
        "".join(
            json.dumps(
                {
                    "entity_id": row["id"],
                    "name": row["name"],
                    "kind": row["kind"],
                    "priority": "high" if row["interview_count"] >= 5 else "normal",
                    "interview_count": row["interview_count"],
                    "mention_count": row["mention_count"],
                    "linked_count": row["linked_count"],
                    "lexicon_count": row["lexicon_count"],
                    "review_status": row["review_status"],
                    "example_source_url": row["example_source_url"],
                    "review_tasks": [
                        "确认规范名称和工具类型",
                        "区分创作者明确推荐、正在使用、过去使用和顺带提及",
                        "补充适用场景与限制条件",
                        "核对原文证据和访谈链接",
                    ],
                },
                ensure_ascii=False,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUT_PATH), "entities": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
