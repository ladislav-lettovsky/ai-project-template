"""Sync check: .agents/skills/ content must stay identical to .claude/skills/.

.agents/skills/ is the Agent Skills portable layer (cross-tool standard); .claude/skills/
is the authoritative source. Any update to a SKILL.md in .claude/skills/ must be reflected
in the corresponding file under .agents/skills/. This test enforces that constraint so
drift is caught at CI time rather than discovered when Codex loads a stale skill copy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
AGENTS_SKILLS = REPO_ROOT / ".agents" / "skills"


def _skill_dirs(base: Path) -> set[str]:
    return {p.name for p in base.iterdir() if p.is_dir()} if base.is_dir() else set()


def test_agents_skills_directory_exists() -> None:
    """The .agents/skills/ directory must be present."""
    assert AGENTS_SKILLS.is_dir(), f"{AGENTS_SKILLS} does not exist"


def test_skill_sets_match() -> None:
    """Both directories must contain exactly the same skill subdirectories."""
    claude_skills = _skill_dirs(CLAUDE_SKILLS)
    agents_skills = _skill_dirs(AGENTS_SKILLS)

    only_in_claude = claude_skills - agents_skills
    only_in_agents = agents_skills - claude_skills

    assert not only_in_claude, (
        f"Skills in .claude/skills/ but missing from .agents/skills/: {sorted(only_in_claude)}\n"
        f"Copy the SKILL.md file(s) to .agents/skills/<skill>/SKILL.md."
    )
    assert not only_in_agents, (
        f"Skills in .agents/skills/ but absent from .claude/skills/: {sorted(only_in_agents)}\n"
        f"Either add a canonical copy under .claude/skills/ or remove the .agents/ entry."
    )


@pytest.mark.parametrize("skill_name", sorted(_skill_dirs(CLAUDE_SKILLS)))
def test_skill_content_is_identical(skill_name: str) -> None:
    """Each SKILL.md in .agents/skills/ must be byte-identical to its .claude/skills/ twin."""
    claude_file = CLAUDE_SKILLS / skill_name / "SKILL.md"
    agents_file = AGENTS_SKILLS / skill_name / "SKILL.md"

    assert claude_file.is_file(), f".claude/skills/{skill_name}/SKILL.md not found"
    assert agents_file.is_file(), (
        f".agents/skills/{skill_name}/SKILL.md not found — "
        f"copy from .claude/skills/{skill_name}/SKILL.md"
    )

    claude_text = claude_file.read_text(encoding="utf-8")
    agents_text = agents_file.read_text(encoding="utf-8")

    assert claude_text == agents_text, (
        f".agents/skills/{skill_name}/SKILL.md differs from .claude/skills/{skill_name}/SKILL.md.\n"
        f"Run: cp .claude/skills/{skill_name}/SKILL.md .agents/skills/{skill_name}/SKILL.md"
    )
