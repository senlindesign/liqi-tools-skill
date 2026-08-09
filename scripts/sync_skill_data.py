#!/usr/bin/env python3
"""Synchronize versioned corpus artifacts into the distributable Skill package."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data"
TARGET = ROOT / "liqi-tools/references/data"
FILES = (
    "interviews-manifest.jsonl",
    "tool-sections.jsonl",
    "entities.provisional.jsonl",
    "review-queue.jsonl",
    "reviewed-tools.jsonl",
    "creator-profiles.jsonl",
    "workflow-cases.jsonl",
    "reviewed-workflow-cases.jsonl",
    "tool-aggregates.jsonl",
    "tool-mentions.schema.json",
    "tool-mentions.sample.jsonl",
    "liqi-tools.sqlite3",
)


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source = SOURCE / name
        if not source.exists():
            raise SystemExit(f"missing source artifact: {source}")
        shutil.copy2(source, TARGET / name)
    interview_source = ROOT / "interviews"
    interview_target = ROOT / "liqi-tools/references/interviews"
    copied_interviews = 0
    for source in interview_source.rglob("*.md"):
        target = interview_target / source.relative_to(interview_source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_interviews += 1
    print(f"synced {len(FILES)} data files and {copied_interviews} interviews")


if __name__ == "__main__":
    main()
