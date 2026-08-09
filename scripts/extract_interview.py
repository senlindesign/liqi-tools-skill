#!/usr/bin/env python3
"""Extract one or more liqi.io interview pages to attributed Markdown."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from site_common import fetch, parse_interview_page, slug_from_url, write_text, yaml_quote


def render(url: str) -> tuple[str, str]:
    page = fetch(url)
    parsed = parse_interview_page(page, url)
    slug = slug_from_url(url)
    frontmatter = [
        "---",
        f"id: {yaml_quote('liqi-' + slug)}",
        f"title: {yaml_quote(parsed.title.strip())}",
        f"published_at: {yaml_quote(parsed.published_at)}",
        f"source_url: {yaml_quote(url)}",
        'source_site: "利器"',
        'license: "CC-BY-NC-SA"',
        'use_policy: "reference-only; not for model training"',
        'extraction_status: "machine-extracted-needs-review"',
        "---",
        "",
        "> 来源：利器。正文按原页面结构进行机器抽取；使用时请保留署名、原链接和许可证。",
        "",
    ]
    body = re.sub(r"(?m)!\[[^\]]*\]\(file://[^)\n]+\)\n?", "> [原页存在未公开的本地图片路径，已在归档中移除]\n", parsed.markdown())
    return slug, "\n".join(frontmatter) + body


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("urls", nargs="+")
    args.add_argument("--output-dir", default="interviews/samples")
    options = args.parse_args()
    for url in options.urls:
        slug, markdown = render(url)
        path = Path(options.output_dir) / f"{slug}.md"
        write_text(path, markdown)
        print(path)


if __name__ == "__main__":
    main()
