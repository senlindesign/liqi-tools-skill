#!/usr/bin/env python3
"""Extract every included interview in the manifest with resume support."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from extract_interview import render
from site_common import write_text


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--manifest", default="data/interviews-manifest.jsonl")
    args.add_argument("--output-dir", default="interviews/full")
    args.add_argument("--force", action="store_true")
    options = args.parse_args()

    records = [json.loads(line) for line in Path(options.manifest).read_text(encoding="utf-8").splitlines()]
    targets = [row for row in records if row["collection_decision"] == "include"]
    output_dir = Path(options.output_dir)
    failures: list[dict[str, str]] = []
    written = skipped = 0

    for index, row in enumerate(targets, 1):
        path = output_dir / f"{row['slug']}.md"
        if path.exists() and not options.force:
            skipped += 1
            continue
        try:
            slug, markdown = render(row["source_url"])
            if slug != row["slug"]:
                raise ValueError(f"slug mismatch: {slug} != {row['slug']}")
            write_text(path, markdown)
            written += 1
        except Exception as exc:  # Preserve the rest of a long batch.
            failures.append({"id": row["id"], "url": row["source_url"], "error": str(exc)})
        if index % 10 == 0 or index == len(targets):
            print(f"progress={index}/{len(targets)} written={written} skipped={skipped} failures={len(failures)}", flush=True)

    failure_path = Path("data/extraction-failures.jsonl")
    failure_payload = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in failures)
    write_text(failure_path, failure_payload)
    summary = {"targets": len(targets), "written": written, "skipped": skipped, "failures": len(failures)}
    print(json.dumps(summary, ensure_ascii=False))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
