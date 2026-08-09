#!/usr/bin/env python3
"""Shared, dependency-free helpers for reading liqi.io."""

from __future__ import annotations

import html
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


USER_AGENT = "liqi-tools-research/0.1 (+https://liqi.io/)"


def fetch(url: str, *, delay: float = 0.5) -> str:
    """Fetch one public page with a descriptive user agent and gentle delay."""
    if delay:
        time.sleep(delay)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class InterviewPageParser(HTMLParser):
    """Extract article metadata and readable Markdown from Hugo article HTML."""

    BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.published_at = ""
        self.word_count = None
        self._stack: list[tuple[str, dict[str, str]]] = []
        self._in_single = False
        self._content_depth = 0
        self._capture_title = False
        self._capture_tip = False
        self._tip_text: list[str] = []
        self._out: list[str] = []
        self._list_stack: list[str] = []
        self._link_stack: list[str] = []
        self._skip_depth = 0

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = self._attrs(attrs)
        self._stack.append((tag, attr))
        classes = set(attr.get("class", "").split())
        if tag == "section" and attr.get("id") == "single":
            self._in_single = True
        if self._in_single and tag == "h1" and "title" in classes and not self._content_depth:
            self._capture_title = True
        if self._in_single and tag == "div" and "tip" in classes and not self._content_depth:
            self._capture_tip = True
        if self._in_single and tag == "div" and "content" in classes:
            self._content_depth = 1
            return
        if not self._content_depth:
            return
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._ensure_blank_line()
            self._out.append("#" * int(tag[1]) + " ")
        elif tag in {"p", "blockquote", "pre"}:
            self._ensure_blank_line()
            if tag == "blockquote":
                self._out.append("> ")
            elif tag == "pre":
                self._out.append("```\n")
        elif tag in {"ul", "ol"}:
            self._ensure_blank_line()
            self._list_stack.append(tag)
        elif tag == "li":
            self._ensure_line_start()
            marker = "- " if not self._list_stack or self._list_stack[-1] == "ul" else "1. "
            self._out.append(marker)
        elif tag == "br":
            self._out.append("  \n")
        elif tag in {"strong", "b"}:
            self._out.append("**")
        elif tag in {"em", "i"}:
            self._out.append("*")
        elif tag == "code" and not self._inside("pre"):
            self._out.append("`")
        elif tag == "a":
            if "anchor" in classes:
                self._link_stack.append("")
                self._skip_depth += 1
            else:
                self._out.append("[")
                self._link_stack.append(urljoin(self.base_url, attr.get("href", "")))
        elif tag == "img":
            src = urljoin(self.base_url, attr.get("src", ""))
            alt = attr.get("alt", "image")
            # Older interviews use the jellyfish logo as a decorative question
            # marker. It carries no source information and breaks Markdown flow.
            if "logo-jellyfish" not in alt:
                self._out.append(f"![{alt}]({src})")

    def handle_endtag(self, tag: str) -> None:
        if self._content_depth:
            if self._skip_depth:
                if tag == "a" and self._link_stack and self._link_stack[-1] == "":
                    self._link_stack.pop()
                    self._skip_depth -= 1
                elif tag in {"script", "style"}:
                    self._skip_depth -= 1
            else:
                if tag in {"strong", "b"}:
                    self._out.append("**")
                elif tag in {"em", "i"}:
                    self._out.append("*")
                elif tag == "code" and not self._inside("pre"):
                    self._out.append("`")
                elif tag == "a" and self._link_stack:
                    href = self._link_stack.pop()
                    self._out.append(f"]({href})")
                elif tag == "pre":
                    self._out.append("\n```\n")
                elif tag in self.BLOCK_TAGS or tag == "li":
                    self._out.append("\n")
                elif tag in {"ul", "ol"}:
                    if self._list_stack:
                        self._list_stack.pop()
                    self._out.append("\n")

        if self._capture_title and tag == "h1":
            self._capture_title = False
        if self._capture_tip and tag == "div":
            self._capture_tip = False
            tip = " ".join("".join(self._tip_text).split())
            date_match = re.search(r"([A-Z][a-z]{2} \d{1,2}, \d{4})", tip)
            if date_match:
                from datetime import datetime

                self.published_at = datetime.strptime(date_match.group(1), "%b %d, %Y").date().isoformat()
            words_match = re.search(r"(\d+) words", tip)
            if words_match:
                self.word_count = int(words_match.group(1))
        if self._content_depth:
            if tag == "div" and self._content_depth == 1:
                self._content_depth = 0
            elif tag == "div":
                self._content_depth -= 1
        if self._in_single and tag == "section":
            self._in_single = False
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self.title += data
        if self._capture_tip:
            self._tip_text.append(data)
        if self._content_depth and not self._skip_depth:
            cleaned = re.sub(r"\s+", " ", html.unescape(data))
            if cleaned.strip():
                if self._out and not self._out[-1].endswith((" ", "\n", "[", "*", "`")):
                    self._out.append(" ")
                self._out.append(cleaned.strip())

    def _inside(self, tag: str) -> bool:
        return any(item_tag == tag for item_tag, _ in self._stack)

    def _ensure_blank_line(self) -> None:
        if not self._out:
            return
        joined = "".join(self._out)
        if not joined.endswith("\n\n"):
            self._out.append("\n\n" if not joined.endswith("\n") else "\n")

    def _ensure_line_start(self) -> None:
        if self._out and not "".join(self._out).endswith("\n"):
            self._out.append("\n")

    def markdown(self) -> str:
        text = "".join(self._out)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?m)^#{1,6}\s*$\n?", "", text)
        text = re.sub(r"(?m)^\*{2,4}\s*$\n?", "", text)
        text = re.sub(r"(?m)^\*\*(#{1,6}) \*\*(.*\*\*)$", r"\1 **\2", text)
        # Repair an old invalid-HTML pattern where a decorative image sits at
        # the start of a bold question and causes the opening marker to detach.
        text = re.sub(r"(?m)^(?!\*\*)([^\n]+[？。])\*\*$", r"**\1**", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def parse_interview_page(page_html: str, url: str) -> InterviewPageParser:
    parser = InterviewPageParser(url)
    parser.feed(page_html)
    return parser


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
