#!/usr/bin/env python3
"""Run deterministic retrieval, ranking, latency, and output-size checks."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "liqi-tools/scripts/search_liqi.py"


def main() -> None:
    cases = [json.loads(line) for line in (ROOT / "data/eval-cases.jsonl").read_text(encoding="utf-8").splitlines()]
    failures = []
    durations = []
    for case in cases:
        command = [sys.executable, str(SCRIPT), case["query"], "--mode", case["mode"], "--limit", str(case.get("limit", 5)), "--json", *case.get("args", [])]
        started = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        duration_ms = round((time.perf_counter() - started) * 1000)
        durations.append(duration_ms)
        problems = []
        if result.returncode:
            problems.append(f"returncode={result.returncode}")
        for value in case.get("must_include", []):
            if value not in result.stdout:
                problems.append(f"missing={value}")
        for value in case.get("must_not_include", []):
            if value in result.stdout:
                problems.append(f"unexpected={value}")
        for left, right in case.get("ordered_before", []):
            if left not in result.stdout or right not in result.stdout or result.stdout.index(left) >= result.stdout.index(right):
                problems.append(f"order={left} before {right}")
        if len(result.stdout.encode("utf-8")) > case.get("max_output_bytes", 12000):
            problems.append(f"output_bytes={len(result.stdout.encode('utf-8'))}")
        if duration_ms > case.get("max_duration_ms", 750):
            problems.append(f"duration_ms={duration_ms}")
        try:
            payload = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            payload = {}
            problems.append("invalid_json")
        if case.get("expected_status") and payload.get("result_status") != case["expected_status"]:
            problems.append(f"status={payload.get('result_status')}")
        top = payload.get("results", [{}])[0] if payload.get("results") else {}
        for value in case.get("top_must_include", []):
            if value not in json.dumps(top, ensure_ascii=False):
                problems.append(f"top_missing={value}")
        if problems:
            failures.append({"id": case["id"], "problems": problems, "stderr": result.stderr})
    if failures:
        print(json.dumps({"status": "FAILED", "failures": failures}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({
        "status": "OK", "cases": len(cases), "max_duration_ms": max(durations),
        "average_duration_ms": round(sum(durations) / len(durations)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
