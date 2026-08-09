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
    assert re.search(r'(?m)^interface:\n(?:.*\n)*?  default_prompt: "Use \$liqi-tools ', agent_text), "default prompt must be nested under interface and invoke $liqi-tools"
    print("Skill structure OK")


if __name__ == "__main__":
    main()
