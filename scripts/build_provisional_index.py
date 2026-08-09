#!/usr/bin/env python3
"""Build a provisional entity index and recover unlinked exact-name mentions."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from site_common import write_text


ROOT = Path(__file__).resolve().parent.parent
BAD_NAMES = {"官网", "网站", "原文", "这里", "更多", "下载", "链接", "参考", "source", "home"}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def normalize_name(name: str) -> str:
    value = unicodedata.normalize("NFKC", name)
    value = re.sub(r"\s+", " ", value).strip(" \t\n\r|,，。:：;；-–—")
    return value.casefold()


def usable_name(name: str) -> bool:
    normalized = normalize_name(name)
    if len(normalized) < 2 or len(normalized) > 90:
        return False
    if normalized in BAD_NAMES or normalized.startswith(("http://", "https://", "video width", "caption ")):
        return False
    if normalized.count("[") or normalized.count("]"):
        return False
    return True


def entity_id(key: str) -> str:
    return "liqi-entity-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def classify_candidate(row: dict) -> str:
    try:
        parsed = urlparse(row["tool_url_raw"])
    except ValueError:
        return row["candidate_kind"]
    host = parsed.netloc.casefold().removeprefix("www.")
    path = parsed.path.casefold()
    media_hosts = ("youtube.com", "youtu.be", "v.qq.com", "bilibili.com", "vimeo.com", "youku.com", "tudou.com")
    article_hosts = ("zhihu.com", "mp.weixin.qq.com", "sspai.com", "medium.com", "jianshu.com")
    if any(host == item or host.endswith("." + item) for item in media_hosts):
        return "media_resource"
    if any(host == item or host.endswith("." + item) for item in article_hosts):
        return "article_resource"
    if any(marker in path for marker in ("/review", "/article", "/blog/", "/posts/")):
        return "article_resource"
    if path.endswith((".pdf", ".epub", ".doc", ".docx")):
        return "document_resource"
    return row["candidate_kind"]


def main() -> None:
    linked = read_jsonl(ROOT / "data/tool-candidates.jsonl")
    sections = read_jsonl(ROOT / "data/tool-sections.jsonl")

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in linked:
        if usable_name(row["tool_name_raw"]):
            grouped[normalize_name(row["tool_name_raw"])].append(row)

    entities = []
    for key, rows in grouped.items():
        spellings = Counter(row["tool_name_raw"].strip() for row in rows)
        canonical = spellings.most_common(1)[0][0]
        kinds = Counter(classify_candidate(row) for row in rows)
        urls = Counter(row["tool_url_raw"] for row in rows)
        entities.append(
            {
                "entity_id": entity_id(key),
                "name": canonical,
                "aliases": [name for name, _ in spellings.most_common() if name != canonical],
                "provisional_kind": kinds.most_common(1)[0][0],
                "urls": [url for url, _ in urls.most_common()],
                "linked_mention_count": len(rows),
                "interview_count": len({row["source_interview_id"] for row in rows}),
                "review_status": "provisional",
            }
        )

    # Use names observed with links as a conservative lexicon for exact matching.
    # Longest-first makes the output easier to review even though overlapping
    # names are deliberately retained until entity normalization.
    lexicon = sorted(grouped, key=len, reverse=True)
    linked_by_section: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in linked:
        linked_by_section[(row["source_interview_id"], row["evidence_heading"])].add(
            normalize_name(row["tool_name_raw"])
        )
    unlinked = []
    for section in sections:
        # Keep visible link labels but remove destinations before exact matching.
        visible_content = re.sub(r"\]\(https?://[^)\s]+\)", "]", section["content"])
        visible_content = re.sub(r"https?://\S+", " ", visible_content)
        content_folded = unicodedata.normalize("NFKC", visible_content).casefold()
        linked_names_here = linked_by_section[(section["source_interview_id"], section["heading"])]
        occupied: list[tuple[int, int]] = []
        for linked_key in sorted(linked_names_here, key=len, reverse=True):
            occupied.extend(match.span() for match in re.finditer(re.escape(linked_key), content_folded))
        for key in lexicon:
            if key in linked_names_here or key not in content_folded:
                continue
            # Require token boundaries for short Latin names to avoid matches
            # such as "R" inside ordinary words.
            pattern = re.escape(key)
            if key.isascii() and len(key) <= 4:
                pattern = rf"(?<![a-z0-9]){pattern}(?![a-z0-9])"
            matches = [match.span() for match in re.finditer(pattern, content_folded)]
            fresh = [
                span
                for span in matches
                if not any(span[0] >= used[0] and span[1] <= used[1] for used in occupied)
            ]
            if not fresh:
                continue
            occupied.extend(fresh)
            source_rows = grouped[key]
            preferred = Counter(row["tool_name_raw"].strip() for row in source_rows).most_common(1)[0][0]
            unlinked.append(
                {
                    "mention_id": f"{section['section_id']}-lexicon-{len(unlinked)+1:06d}",
                    "entity_id": entity_id(key),
                    "tool_name_matched": preferred,
                    "match_method": "exact_link_lexicon",
                    "candidate_kind": Counter(row["candidate_kind"] for row in source_rows).most_common(1)[0][0],
                    "evidence_heading": section["heading"],
                    "evidence_context": section["content"],
                    "source_interview_id": section["source_interview_id"],
                    "source_url": section["source_url"],
                    "review_status": "machine_candidate",
                }
            )

    entities.sort(key=lambda row: (-row["interview_count"], row["name"].casefold()))
    write_text(
        ROOT / "data/entities.provisional.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in entities),
    )
    write_text(
        ROOT / "data/unlinked-candidates.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in unlinked),
    )
    print(
        json.dumps(
            {
                "provisional_entities": len(entities),
                "unlinked_exact_matches": len(unlinked),
                "interviews_with_unlinked_matches": len({row["source_interview_id"] for row in unlinked}),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
