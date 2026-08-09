#!/usr/bin/env python3
"""Release gate for the GitHub-ready Skill bundle."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "liqi-tools"


def main() -> None:
    required = [
        SKILL / "SKILL.md",
        SKILL / "agents/openai.yaml",
        SKILL / "scripts/search_liqi.py",
        SKILL / "references/data/liqi-tools.sqlite3",
        SKILL / "references/data/reviewed-tools.jsonl",
        SKILL / "references/data/review-queue.jsonl",
        SKILL / "references/data/creator-profiles.jsonl",
        SKILL / "references/data/workflow-cases.jsonl",
        SKILL / "references/data/tool-aggregates.jsonl",
        SKILL / "references/data/reviewed-workflow-cases.jsonl",
        ROOT / "data/eval-cases.jsonl",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing release files: " + ", ".join(missing))

    connection = sqlite3.connect(SKILL / "references/data/liqi-tools.sqlite3")
    counts = {
        table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("interviews", "sections", "entities", "mentions", "reviewed_mentions", "creator_profiles", "workflow_cases", "reviewed_workflow_cases", "tool_aggregates")
    }
    connection.close()
    assert counts == {"interviews": 251, "sections": 848, "entities": 2983, "mentions": 7712, "reviewed_mentions": 40, "creator_profiles": 251, "workflow_cases": 848, "reviewed_workflow_cases": 6, "tool_aggregates": 2983}, counts

    reviewed = [json.loads(line) for line in (SKILL / "references/data/reviewed-tools.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(reviewed) == 40
    assert all(row["review_status"] == "reviewed" for row in reviewed)
    leaked_paths = [path for path in SKILL.rglob("*") if path.is_file() and "file://" in path.read_text(encoding="utf-8", errors="ignore")]
    assert not leaked_paths, "local file URI in release package: " + ", ".join(str(path.relative_to(ROOT)) for path in leaked_paths)
    evaluation = subprocess.run([sys.executable, str(ROOT / "scripts/run_evals.py")], cwd=ROOT, text=True, capture_output=True, check=False)
    assert evaluation.returncode == 0, evaluation.stdout + evaluation.stderr
    print(json.dumps({"skill": str(SKILL), "database": counts, "reviewed_batch": len(reviewed), "status": "READY_CANDIDATE"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
