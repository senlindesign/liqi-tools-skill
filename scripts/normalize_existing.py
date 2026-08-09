#!/usr/bin/env python3
"""Apply safe Markdown normalizations to already extracted interview files."""

from __future__ import annotations

import re
from pathlib import Path


def normalize(text: str) -> str:
    text = re.sub(r"(?m)^\*\*(#{1,6}) \*\*(.*\*\*)$", r"\1 **\2", text)
    text = re.sub(r"(?m)^#{1,6}\s*$\n?", "", text)
    text = re.sub(
        r"(?m)!\[[^\]]*\]\(file://[^)\n]+\)\n?",
        "> [原页存在未公开的本地图片路径，已在归档中移除]\n",
        text,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "interviews"
    changed = 0
    for path in sorted(root.rglob("*.md")):
        original = path.read_text(encoding="utf-8")
        updated = normalize(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"normalized={changed}")


if __name__ == "__main__":
    main()
