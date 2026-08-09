#!/usr/bin/env python3
"""Run deterministic retrieval checks for the public Liqi Tools Skill."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "liqi-tools/scripts/search_liqi.py"


def main() -> None:
    cases = [json.loads(line) for line in (ROOT / "data/eval-cases.jsonl").read_text(encoding="utf-8").splitlines()]
    failures = []
    for case in cases:
        command = [sys.executable, str(SCRIPT), case["query"], "--mode", case["mode"], "--limit", "5", *case["args"]]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        missing = [value for value in case["must_include"] if value not in result.stdout]
        if result.returncode or missing:
            failures.append({"id": case["id"], "returncode": result.returncode, "missing": missing, "stderr": result.stderr})
    if failures:
        print(json.dumps({"status": "FAILED", "failures": failures}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"status": "OK", "cases": len(cases)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
