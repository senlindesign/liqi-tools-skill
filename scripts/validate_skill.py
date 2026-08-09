#!/usr/bin/env python3
"""Portable structural validation for the distributable Agent Skills package."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "liqi-tools"


def main() -> None:
    skill_md = SKILL / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with YAML frontmatter"
    frontmatter = match.group(1)
    name = re.search(r"(?m)^name:\s*([^\n]+)$", frontmatter)
    description = re.search(r"(?m)^description:\s*([^\n]+)$", frontmatter)
    assert name and name.group(1).strip() == "liqi-tools", "skill name must be liqi-tools"
    assert description and len(description.group(1).strip()) >= 40, "description is missing or too short"
    assert re.fullmatch(r"[a-z0-9-]+", name.group(1).strip()), "skill name contains invalid characters"
    assert (SKILL / "scripts/search_liqi.py").exists(), "search script missing"
    agent_yaml = SKILL / "agents/openai.yaml"
    assert agent_yaml.exists(), "OpenAI agent metadata missing"
    agent_text = agent_yaml.read_text(encoding="utf-8")
    interface = re.search(r'(?ms)^interface:\n(?P<body>(?:  .*\n)+)', agent_text)
    assert interface, "openai.yaml must contain an interface mapping"
    assert re.search(r'^  display_name: ".+"$', interface.group("body"), re.MULTILINE), "display_name missing"
    assert re.search(r'^  short_description: ".{10,}"$', interface.group("body"), re.MULTILINE), "short_description missing"
    prompt = re.search(r'^  default_prompt: "(.+)"$', interface.group("body"), re.MULTILINE)
    assert prompt and "$liqi-tools" in prompt.group(1), "default prompt must invoke $liqi-tools"
    print("Skill structure OK")


if __name__ == "__main__":
    main()
