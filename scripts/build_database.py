#!/usr/bin/env python3
"""Build the local SQLite retrieval database from auditable JSONL layers."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from build_provisional_index import entity_id, normalize_name


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data/liqi-tools.sqlite3"


def read_jsonl(name: str) -> list[dict]:
    path = ROOT / "data" / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE interviews (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  published_at TEXT NOT NULL,
  source_url TEXT NOT NULL UNIQUE,
  tags_json TEXT NOT NULL,
  article_type TEXT NOT NULL
);
CREATE TABLE sections (
  id TEXT PRIMARY KEY,
  interview_id TEXT NOT NULL REFERENCES interviews(id),
  heading TEXT NOT NULL,
  content TEXT NOT NULL
);
CREATE TABLE entities (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  linked_mention_count INTEGER NOT NULL,
  interview_count INTEGER NOT NULL,
  review_status TEXT NOT NULL
);
CREATE TABLE aliases (
  entity_id TEXT NOT NULL REFERENCES entities(id),
  alias TEXT NOT NULL,
  PRIMARY KEY (entity_id, alias)
);
CREATE TABLE entity_urls (
  entity_id TEXT NOT NULL REFERENCES entities(id),
  url TEXT NOT NULL,
  PRIMARY KEY (entity_id, url)
);
CREATE TABLE mentions (
  id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities(id),
  section_id TEXT NOT NULL REFERENCES sections(id),
  interview_id TEXT NOT NULL REFERENCES interviews(id),
  name_raw TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  heading TEXT NOT NULL,
  context TEXT NOT NULL,
  source_url TEXT NOT NULL,
  review_status TEXT NOT NULL
);
CREATE TABLE reviewed_mentions (
  review_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities(id),
  entity_name TEXT NOT NULL,
  tool_type TEXT NOT NULL,
  creator TEXT NOT NULL,
  interview_id TEXT NOT NULL REFERENCES interviews(id),
  source_url TEXT NOT NULL,
  use_case TEXT NOT NULL,
  recommendation_strength TEXT NOT NULL,
  evidence TEXT NOT NULL,
  review_batch TEXT NOT NULL,
  review_status TEXT NOT NULL
);
CREATE TABLE creator_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  title TEXT NOT NULL,
  interview_id TEXT NOT NULL REFERENCES interviews(id),
  source_url TEXT NOT NULL,
  published_at TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  article_type TEXT NOT NULL,
  workflow_count INTEGER NOT NULL,
  case_ids_json TEXT NOT NULL,
  stages_json TEXT NOT NULL,
  tool_names_json TEXT NOT NULL,
  tool_entity_ids_json TEXT NOT NULL,
  focus_areas_json TEXT NOT NULL,
  review_status TEXT NOT NULL
);
CREATE TABLE workflow_cases (
  id TEXT PRIMARY KEY,
  creator_id TEXT NOT NULL REFERENCES creator_profiles(id),
  interview_id TEXT NOT NULL REFERENCES interviews(id),
  creator TEXT NOT NULL,
  role TEXT NOT NULL,
  title TEXT NOT NULL,
  stage TEXT NOT NULL,
  tools_json TEXT NOT NULL,
  tool_entity_ids_json TEXT NOT NULL,
  evidence TEXT NOT NULL,
  source_url TEXT NOT NULL,
  review_status TEXT NOT NULL
);
CREATE TABLE reviewed_workflow_cases (
  id TEXT PRIMARY KEY,
  task TEXT NOT NULL,
  creator TEXT NOT NULL,
  role TEXT NOT NULL,
  interview_id TEXT NOT NULL REFERENCES interviews(id),
  source_url TEXT NOT NULL,
  stages_json TEXT NOT NULL,
  principles_json TEXT NOT NULL,
  limitations_json TEXT NOT NULL,
  evidence TEXT NOT NULL,
  review_batch TEXT NOT NULL,
  review_status TEXT NOT NULL
);
CREATE TABLE tool_aggregates (
  entity_id TEXT PRIMARY KEY REFERENCES entities(id),
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  creator_count INTEGER NOT NULL,
  mention_count INTEGER NOT NULL,
  reviewed_count INTEGER NOT NULL,
  recommendation_strengths_json TEXT NOT NULL,
  use_cases_json TEXT NOT NULL,
  creator_ids_json TEXT NOT NULL,
  source_urls_json TEXT NOT NULL,
  review_status TEXT NOT NULL
);
CREATE INDEX mentions_entity_idx ON mentions(entity_id);
CREATE INDEX mentions_interview_idx ON mentions(interview_id);
"""


def local_context(context: str, name: str, radius: int = 220) -> str:
    """Keep evidence close to the mentioned entity, not the whole answer."""
    plain = re.sub(r"!?(\[([^\]]*)\])\((https?://[^)\s]+)\)", r"\2", context)
    folded = plain.casefold()
    position = folded.find(name.casefold())
    if position < 0:
        return " ".join(plain[: radius * 2].split())
    start = max(0, position - radius)
    end = min(len(plain), position + len(name) + radius)
    return ("…" if start else "") + " ".join(plain[start:end].split()) + ("…" if end < len(plain) else "")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    connection = sqlite3.connect(DB_PATH)
    connection.executescript(SCHEMA)

    manifest = [row for row in read_jsonl("interviews-manifest.jsonl") if row["collection_decision"] == "include"]
    sections = read_jsonl("tool-sections.jsonl")
    entities = read_jsonl("entities.provisional.jsonl")
    linked = read_jsonl("tool-candidates.jsonl")
    unlinked = read_jsonl("unlinked-candidates.jsonl")
    reviewed_path = ROOT / "data/reviewed-tools.jsonl"
    reviewed = read_jsonl("reviewed-tools.jsonl") if reviewed_path.exists() else []
    profiles = read_jsonl("creator-profiles.jsonl")
    cases = read_jsonl("workflow-cases.jsonl")
    aggregates = read_jsonl("tool-aggregates.jsonl")
    reviewed_cases_path = ROOT / "data/reviewed-workflow-cases.jsonl"
    reviewed_cases = read_jsonl("reviewed-workflow-cases.jsonl") if reviewed_cases_path.exists() else []

    connection.executemany(
        "INSERT INTO interviews VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                row["id"],
                row["title"],
                row["published_at"],
                row["source_url"],
                json.dumps(row["tags"], ensure_ascii=False),
                row["article_type"],
            )
            for row in manifest
        ],
    )
    connection.executemany(
        "INSERT INTO sections VALUES (?, ?, ?, ?)",
        [(row["section_id"], row["source_interview_id"], row["heading"], row["content"]) for row in sections],
    )
    connection.executemany(
        "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                row["entity_id"],
                row["name"],
                row["provisional_kind"],
                row["linked_mention_count"],
                row["interview_count"],
                row["review_status"],
            )
            for row in entities
        ],
    )
    connection.executemany(
        "INSERT INTO aliases VALUES (?, ?)",
        [(row["entity_id"], alias) for row in entities for alias in row["aliases"]],
    )
    connection.executemany(
        "INSERT INTO entity_urls VALUES (?, ?)",
        [(row["entity_id"], url) for row in entities for url in row["urls"]],
    )

    section_ids = {row["section_id"] for row in sections}
    linked_mentions = []
    for row in linked:
        if not (2 <= len(normalize_name(row["tool_name_raw"])) <= 90):
            continue
        section_id = row["candidate_id"].rsplit("-candidate-", 1)[0]
        eid = entity_id(normalize_name(row["tool_name_raw"]))
        if section_id not in section_ids or not connection.execute("SELECT 1 FROM entities WHERE id=?", (eid,)).fetchone():
            continue
        linked_mentions.append(
            (
                row["candidate_id"], eid, section_id, row["source_interview_id"], row["tool_name_raw"],
                "linked", row["evidence_heading"], local_context(row["evidence_context"], row["tool_name_raw"]),
                row["source_url"], row["review_status"],
            )
        )
    unlinked_mentions = []
    for row in unlinked:
        section_id = row["mention_id"].rsplit("-lexicon-", 1)[0]
        unlinked_mentions.append(
            (
                row["mention_id"], row["entity_id"], section_id, row["source_interview_id"],
                row["tool_name_matched"], "lexicon_match", row["evidence_heading"],
                local_context(row["evidence_context"], row["tool_name_matched"]),
                row["source_url"], row["review_status"],
            )
        )
    connection.executemany("INSERT INTO mentions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", linked_mentions + unlinked_mentions)
    connection.executemany(
        "INSERT INTO reviewed_mentions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row["review_id"], entity_id(normalize_name(row["entity_name"])), row["entity_name"],
                row["tool_type"], row["creator"], row["source_interview_id"], row["source_url"],
                row["use_case"], row["recommendation_strength"], row["evidence"],
                row["review_batch"], row["review_status"],
            )
            for row in reviewed
        ],
    )
    connection.executemany(
        "INSERT INTO creator_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row["creator_id"], row["name"], row["role"], row["title"], row["source_interview_id"],
                row["source_url"], row["published_at"], json.dumps(row["tags"], ensure_ascii=False),
                row["article_type"], row["workflow_count"], json.dumps(row["case_ids"], ensure_ascii=False),
                json.dumps(row["stages"], ensure_ascii=False), json.dumps(row["tool_names"], ensure_ascii=False),
                json.dumps(row["tool_entity_ids"], ensure_ascii=False), json.dumps(row["focus_areas"], ensure_ascii=False),
                row["review_status"],
            )
            for row in profiles
        ],
    )
    connection.executemany(
        "INSERT INTO workflow_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row["case_id"], row["creator_id"], row["source_interview_id"], row["creator"], row["role"],
                row["title"], row["stage"], json.dumps(row["tools"], ensure_ascii=False),
                json.dumps(row["tool_entity_ids"], ensure_ascii=False), row["evidence"], row["source_url"],
                row["review_status"],
            )
            for row in cases
        ],
    )
    connection.executemany(
        "INSERT INTO reviewed_workflow_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row["case_id"], row["task"], row["creator"], row["role"], row["source_interview_id"],
                row["source_url"], json.dumps(row["stages"], ensure_ascii=False),
                json.dumps(row["principles"], ensure_ascii=False), json.dumps(row["limitations"], ensure_ascii=False),
                row["evidence"], row["review_batch"], row["review_status"],
            )
            for row in reviewed_cases
        ],
    )
    connection.executemany(
        "INSERT INTO tool_aggregates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row["entity_id"], row["name"], row["kind"], row["creator_count"], row["mention_count"],
                row["reviewed_count"], json.dumps(row["recommendation_strengths"], ensure_ascii=False),
                json.dumps(row["use_cases"], ensure_ascii=False), json.dumps(row["creator_ids"], ensure_ascii=False),
                json.dumps(row["source_urls"], ensure_ascii=False), row["review_status"],
            )
            for row in aggregates
        ],
    )
    connection.commit()

    counts = {
        table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("interviews", "sections", "entities", "mentions", "reviewed_mentions", "creator_profiles", "workflow_cases", "reviewed_workflow_cases", "tool_aggregates")
    }
    connection.close()
    print(json.dumps({"database": str(DB_PATH), **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
