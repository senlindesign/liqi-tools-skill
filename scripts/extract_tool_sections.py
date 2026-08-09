#!/usr/bin/env python3
"""Create auditable tool-related sections and linked tool candidates."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from site_common import write_text


ROOT = Path(__file__).resolve().parent.parent
SECTION_KEYWORDS = (
    "硬件",
    "软件",
    "工具",
    "利器",
    "装备",
    "设备",
    "信息源",
    "应用",
    "app",
    "使用哪些",
    "都在使用",
    "推荐",
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_QUESTION_RE = re.compile(r"^\*\*(.+(?:[？?。]|呢？))\*\*$")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)")


def frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf'(?m)^{re.escape(key)}: "([^"]*)"$', text)
    return match.group(1) if match else ""


def clean_heading(value: str) -> str:
    return re.sub(r"[*_`#]", "", value).strip()


def is_tool_section(heading: str) -> bool:
    lowered = heading.lower()
    return any(keyword in lowered for keyword in SECTION_KEYWORDS)


def split_sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    heading = "导言"
    lines: list[str] = []
    for line in body.splitlines():
        heading_match = HEADING_RE.match(line)
        bold_match = BOLD_QUESTION_RE.match(line)
        if heading_match or bold_match:
            if lines:
                sections.append((heading, lines))
            raw_heading = heading_match.group(2) if heading_match else bold_match.group(1)
            heading = clean_heading(raw_heading)
            lines = []
        else:
            lines.append(line)
    if lines:
        sections.append((heading, lines))
    return [(name, "\n".join(content).strip()) for name, content in sections if "\n".join(content).strip()]


def candidate_kind(heading: str) -> str:
    lowered = heading.lower()
    if "硬件" in lowered or "装备" in lowered or "设备" in lowered:
        return "hardware"
    if "软件" in lowered or "app" in lowered or "应用" in lowered:
        return "software"
    if "信息源" in lowered:
        return "information_source"
    if "推荐" in lowered or "利器" in lowered:
        return "recommended_resource"
    return "unknown"


def should_skip_link(name: str, url: str) -> bool:
    lowered_name = name.lower().strip()
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return True
    if not lowered_name or lowered_name in {"加入利器社群", "利器", "下载", "官网", "这里", "链接"}:
        return True
    if host in {"liqi.io", "www.liqi.io"} and ("community" in url or "tags" in url):
        return True
    return False


def main() -> None:
    section_rows = []
    candidate_rows = []
    for path in sorted((ROOT / "interviews/full").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        interview_id = frontmatter_value(text, "id")
        title = frontmatter_value(text, "title")
        source_url = frontmatter_value(text, "source_url")
        body = text.split("---", 2)[-1].strip()
        selected_number = 0
        for heading, content in split_sections(body):
            if not is_tool_section(heading):
                continue
            selected_number += 1
            section_id = f"{interview_id}-section-{selected_number:02d}"
            section_rows.append(
                {
                    "section_id": section_id,
                    "source_interview_id": interview_id,
                    "interview_title": title,
                    "heading": heading,
                    "content": content,
                    "source_url": source_url,
                    "review_status": "machine_selected",
                }
            )
            seen = set()
            for name, url in LINK_RE.findall(content):
                name = " ".join(name.split())
                if should_skip_link(name, url) or (name.casefold(), url) in seen:
                    continue
                seen.add((name.casefold(), url))
                candidate_rows.append(
                    {
                        "candidate_id": f"{section_id}-candidate-{len(seen):02d}",
                        "tool_name_raw": name,
                        "tool_url_raw": url,
                        "candidate_kind": candidate_kind(heading),
                        "evidence_heading": heading,
                        "evidence_context": content,
                        "source_interview_id": interview_id,
                        "source_url": source_url,
                        "review_status": "machine_candidate",
                    }
                )

    write_text(
        ROOT / "data/tool-sections.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in section_rows),
    )
    write_text(
        ROOT / "data/tool-candidates.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidate_rows),
    )
    covered = len({row["source_interview_id"] for row in section_rows})
    candidates_covered = len({row["source_interview_id"] for row in candidate_rows})
    print(
        json.dumps(
            {
                "tool_sections": len(section_rows),
                "interviews_with_sections": covered,
                "linked_candidates": len(candidate_rows),
                "interviews_with_linked_candidates": candidates_covered,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
