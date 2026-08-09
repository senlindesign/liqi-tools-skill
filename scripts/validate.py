#!/usr/bin/env python3
"""Validate the phase-one Liqi corpus artifacts without third-party packages."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from build_provisional_index import entity_id as entity_id_from_name, normalize_name


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_MENTION_FIELDS = {
    "mention_id",
    "tool_name_raw",
    "tool_name_canonical",
    "tool_type",
    "creator",
    "use_case",
    "mention_kind",
    "evidence",
    "evidence_heading",
    "source_interview_id",
    "source_url",
    "confidence",
}
REQUIRED_REVIEW_FIELDS = {
    "review_id", "entity_name", "tool_type", "creator", "source_interview_id", "source_url",
    "use_case", "recommendation_strength", "evidence", "review_batch", "review_status",
}
REQUIRED_REVIEWED_CASE_FIELDS = {
    "case_id", "task", "creator", "role", "source_interview_id", "source_url", "stages",
    "principles", "limitations", "evidence", "review_batch", "review_status",
}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AssertionError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def main() -> None:
    manifest = read_jsonl(ROOT / "data/interviews-manifest.jsonl")
    assert len(manifest) == 254, f"expected 254 manifest rows, found {len(manifest)}"
    assert len({row["id"] for row in manifest}) == len(manifest), "duplicate manifest id"
    assert len({row["source_url"] for row in manifest}) == len(manifest), "duplicate source URL"
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["published_at"]) for row in manifest)
    included_ids = {row["id"] for row in manifest if row["collection_decision"] == "include"}
    assert len(included_ids) == 251, f"expected 251 included interviews, found {len(included_ids)}"

    samples = sorted((ROOT / "interviews/samples").glob("*.md"))
    assert len(samples) == 3, f"expected 3 sample interviews, found {len(samples)}"
    for path in samples:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{path}: missing YAML frontmatter"
        assert "source_url: \"https://liqi.io/" in text, f"{path}: missing source URL"
        assert "license: \"CC-BY-NC-SA\"" in text, f"{path}: missing license"
        assert not re.search(r"(?m)^#{1,6}\s*$", text), f"{path}: empty heading"
        assert "file://" not in text, f"{path}: leaked local file URI"

    full_dir = ROOT / "interviews/full"
    full = sorted(full_dir.glob("*.md")) if full_dir.exists() else []
    if full:
        assert len(full) == len(included_ids), f"expected {len(included_ids)} full interviews, found {len(full)}"
        full_ids = set()
        for path in full:
            text = path.read_text(encoding="utf-8")
            id_match = re.search(r'(?m)^id: "([^"]+)"$', text)
            assert id_match, f"{path}: missing id"
            full_ids.add(id_match.group(1))
            assert len(text) > 300, f"{path}: suspiciously short extraction"
            assert "source_url: \"https://liqi.io/" in text, f"{path}: missing source URL"
            assert not re.search(r"(?m)^#{1,6}\s*$", text), f"{path}: empty heading"
            assert not re.search(r"(?m)^\*\*#{1,6} \*\*", text), f"{path}: malformed bold heading"
            assert "file://" not in text, f"{path}: leaked local file URI"
        assert full_ids == included_ids, "full interview IDs do not match manifest"

    mentions = read_jsonl(ROOT / "data/tool-mentions.sample.jsonl")
    assert mentions, "tool mention sample is empty"
    for row in mentions:
        missing = REQUIRED_MENTION_FIELDS - row.keys()
        assert not missing, f"{row.get('mention_id')}: missing {sorted(missing)}"
        assert row["source_interview_id"] in included_ids, f"{row['mention_id']}: unknown interview"
        assert row["mention_kind"] in {"recommended", "used", "formerly_used", "not_recommended", "editorial"}
        assert row["confidence"] in {"high", "medium", "low"}

    sections_path = ROOT / "data/tool-sections.jsonl"
    candidates_path = ROOT / "data/tool-candidates.jsonl"
    sections = read_jsonl(sections_path) if sections_path.exists() else []
    candidates = read_jsonl(candidates_path) if candidates_path.exists() else []
    for row in sections:
        assert row["source_interview_id"] in included_ids, f"{row['section_id']}: unknown interview"
        assert row["heading"] and row["content"], f"{row['section_id']}: empty section"
    section_ids = {row["section_id"] for row in sections}
    for row in candidates:
        parent = row["candidate_id"].rsplit("-candidate-", 1)[0]
        assert parent in section_ids, f"{row['candidate_id']}: missing section"
        assert row["tool_name_raw"] and row["tool_url_raw"].startswith("http")

    entities_path = ROOT / "data/entities.provisional.jsonl"
    unlinked_path = ROOT / "data/unlinked-candidates.jsonl"
    review_queue_path = ROOT / "data/review-queue.jsonl"
    reviewed_path = ROOT / "data/reviewed-tools.jsonl"
    profiles_path = ROOT / "data/creator-profiles.jsonl"
    cases_path = ROOT / "data/workflow-cases.jsonl"
    aggregates_path = ROOT / "data/tool-aggregates.jsonl"
    reviewed_cases_path = ROOT / "data/reviewed-workflow-cases.jsonl"
    entities = read_jsonl(entities_path) if entities_path.exists() else []
    unlinked = read_jsonl(unlinked_path) if unlinked_path.exists() else []
    entity_ids = {row["entity_id"] for row in entities}
    assert len(entity_ids) == len(entities), "duplicate provisional entity id"
    for row in unlinked:
        assert row["entity_id"] in entity_ids, f"{row['mention_id']}: missing entity"
        assert row["source_interview_id"] in included_ids, f"{row['mention_id']}: unknown interview"
    review_queue = read_jsonl(review_queue_path) if review_queue_path.exists() else []
    assert len(review_queue) == len(entities), "review queue must cover every provisional entity"
    assert {row["entity_id"] for row in review_queue} == entity_ids, "review queue/entity mismatch"
    reviewed = read_jsonl(reviewed_path) if reviewed_path.exists() else []
    assert len({row["review_id"] for row in reviewed}) == len(reviewed), "duplicate review id"
    for row in reviewed:
        missing = REQUIRED_REVIEW_FIELDS - row.keys()
        assert not missing, f"{row.get('review_id')}: missing {sorted(missing)}"
        assert row["source_interview_id"] in included_ids, f"{row['review_id']}: unknown interview"
        assert row["source_url"].startswith("https://liqi.io/"), f"{row['review_id']}: bad source URL"
        assert row["review_status"] == "reviewed"
        assert row["recommendation_strength"] in {"explicit_recommendation", "used", "formerly_used", "not_recommended", "mention_only"}
        assert entity_id_from_name(normalize_name(row["entity_name"])) in entity_ids, f"{row['review_id']}: unknown entity"
    profiles = read_jsonl(profiles_path) if profiles_path.exists() else []
    cases = read_jsonl(cases_path) if cases_path.exists() else []
    aggregates = read_jsonl(aggregates_path) if aggregates_path.exists() else []
    assert len(profiles) == len(included_ids), "creator profile coverage mismatch"
    assert {row["source_interview_id"] for row in profiles} == included_ids, "creator profile/interview mismatch"
    assert all(row.get("case_ids") is not None and row.get("stages") is not None and row.get("tool_names") is not None for row in profiles), "creator profile enrichment missing"
    assert len(cases) == len(sections), "workflow case/section mismatch"
    assert len(aggregates) == len(entities), "tool aggregate/entity mismatch"
    reviewed_cases = read_jsonl(reviewed_cases_path) if reviewed_cases_path.exists() else []
    assert len({row["case_id"] for row in reviewed_cases}) == len(reviewed_cases), "duplicate reviewed workflow case id"
    for row in reviewed_cases:
        missing = REQUIRED_REVIEWED_CASE_FIELDS - row.keys()
        assert not missing, f"{row.get('case_id')}: missing {sorted(missing)}"
        assert row["source_interview_id"] in included_ids, f"{row['case_id']}: unknown interview"
        assert row["source_url"].startswith("https://liqi.io/"), f"{row['case_id']}: bad source URL"
        assert row["review_status"] == "reviewed_case", f"{row['case_id']}: bad reviewed case status"
        assert row["stages"], f"{row['case_id']}: missing stages"

    database_path = ROOT / "data/liqi-tools.sqlite3"
    database_counts = {}
    if database_path.exists():
        connection = sqlite3.connect(database_path)
        database_counts = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("interviews", "sections", "entities", "mentions", "reviewed_mentions", "creator_profiles", "workflow_cases", "reviewed_workflow_cases", "tool_aggregates")
        }
        connection.close()
        assert database_counts["interviews"] == len(included_ids)
        assert database_counts["sections"] == len(sections)
        assert database_counts["entities"] == len(entities)

    print(
        json.dumps(
            {
                "manifest": len(manifest),
                "included_interviews": len(included_ids),
                "sample_markdown": len(samples),
                "sample_tool_mentions": len(mentions),
                "full_markdown": len(full),
                "tool_sections": len(sections),
                "linked_tool_candidates": len(candidates),
                "provisional_entities": len(entities),
                "unlinked_tool_candidates": len(unlinked),
                "review_queue": len(review_queue),
                "reviewed_tools": len(reviewed),
                "creator_profiles": len(profiles),
                "workflow_cases": len(cases),
                "tool_aggregates": len(aggregates),
                "reviewed_workflow_cases": len(reviewed_cases),
                "database": database_counts,
                "status": "OK",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
