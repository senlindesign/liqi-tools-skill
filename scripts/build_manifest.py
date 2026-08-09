#!/usr/bin/env python3
"""Build a JSONL manifest from liqi.io's interview category page."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from site_common import fetch, slug_from_url, write_text


SOURCE_URL = "https://liqi.io/categories/interview/"


class ArchiveParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[dict] = []
        self.year = ""
        self.current: dict | None = None
        self._in_archive = False
        self._capture: str | None = None
        self._text: list[str] = []
        self._title_link = False
        self._in_tags = False

    def handle_starttag(self, tag, attrs):
        attr = {key: value or "" for key, value in attrs}
        classes = set(attr.get("class", "").split())
        if tag == "section" and attr.get("id") == "archive":
            self._in_archive = True
        if not self._in_archive:
            return
        if tag == "h3" and "key" in classes:
            self._capture, self._text = "year", []
        elif tag == "div" and "value" in classes:
            self.current = {"date_label": "", "title": "", "url": "", "tags": []}
        elif self.current is not None and tag == "div" and "date" in classes:
            self._capture, self._text = "date", []
        elif self.current is not None and tag == "div" and "tags" in classes:
            self._in_tags = True
        elif self.current is not None and tag == "a":
            if self._in_tags:
                self._capture, self._text = "tag", []
            elif not self.current["url"]:
                self.current["url"] = attr.get("href", "")
                self._title_link = True
                self._capture, self._text = "title", []

    def handle_endtag(self, tag):
        if self._capture == "year" and tag == "h3":
            self.year = "".join(self._text).strip()
            self._capture = None
        elif self._capture == "date" and tag == "div":
            assert self.current is not None
            self.current["date_label"] = "".join(self._text).strip()
            self._capture = None
        elif self._capture == "title" and tag == "a" and self._title_link:
            assert self.current is not None
            self.current["title"] = " ".join("".join(self._text).split())
            self._capture = None
            self._title_link = False
        elif self._capture == "tag" and tag == "a":
            assert self.current is not None
            tag_text = " ".join("".join(self._text).split())
            if tag_text:
                self.current["tags"].append(tag_text)
            self._capture = None
        if self._in_tags and tag == "div":
            self._in_tags = False
        if self.current is not None and tag == "div" and self.current["url"] and self.current["title"]:
            # Hugo closes .title before .value; delay is unnecessary because tags have
            # already been encountered when present in the minified source.
            if not self._in_tags and self._capture is None:
                entry = dict(self.current)
                entry["year"] = self.year
                self.entries.append(entry)
                self.current = None
        if self._in_archive and tag == "section":
            self._in_archive = False

    def handle_data(self, data):
        if self._capture:
            self._text.append(data)


def classify(title: str) -> tuple[str, str]:
    lowered = title.lower()
    if "城堡" in title or "周刊" in title or "周报" in title:
        return "editorial_or_collection", "exclude"
    if "播客" in title:
        return "podcast_interview", "include"
    if "vlog" in lowered:
        return "vlog_interview", "include"
    if "通信者" in title:
        return "telecom_interview", "include"
    return "creator_interview", "include"


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--output", default="data/interviews-manifest.jsonl")
    args.add_argument("--html", help="Parse a previously downloaded category page")
    options = args.parse_args()
    page = Path(options.html).read_text(encoding="utf-8") if options.html else fetch(SOURCE_URL, delay=0)
    parser = ArchiveParser()
    parser.feed(page)
    records = []
    for index, item in enumerate(parser.entries, 1):
        date = datetime.strptime(f"{item['date_label']} {item['year']}", "%b %d %Y").date().isoformat()
        article_type, decision = classify(item["title"])
        records.append(
            {
                "id": f"liqi-{slug_from_url(item['url'])}",
                "title": item["title"],
                "published_at": date,
                "source_url": item["url"],
                "slug": slug_from_url(item["url"]),
                "tags": item["tags"],
                "article_type": article_type,
                "collection_decision": decision,
                "source_index": index,
                "extraction_status": "pending",
            }
        )
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)
    write_text(Path(options.output), payload)
    included = sum(row["collection_decision"] == "include" for row in records)
    print(json.dumps({"records": len(records), "included": included, "output": options.output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
