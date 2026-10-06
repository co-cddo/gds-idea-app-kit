"""Tests that the agent skill in skills/idea-app-usage stays in step with the CLI and the templates.

The skill is read by AI agents to decide which commands to run and which files they may edit, so a
stale command, flag, project type or file-ownership table means agents give wrong instructions.
"""

import re
from pathlib import Path

import click
import pytest

from gds_idea_app_kit import PKG_REPO_PREFIX, REPO_PREFIX
from gds_idea_app_kit.cli import cli
from gds_idea_app_kit.manifest import get_tracked_files

SKILL_DIR = Path(__file__).parent.parent / "skills" / "idea-app-usage"
SKILL = SKILL_DIR / "SKILL.md"
PROGRAM = "idea-app"

init_command = cli.commands["init"]
PROJECT_TYPES = next(p for p in init_command.params if p.name == "framework").type.choices


def _skill_text() -> str:
    return SKILL.read_text()


def _frontmatter(text: str) -> dict[str, str]:
    assert text.startswith("---\n"), "SKILL.md must start with frontmatter"
    block = text.split("\n---\n", 1)[0].removeprefix("---\n")
    return dict(
        line.split(": ", 1)
        for line in block.splitlines()
        if ": " in line and not line.startswith(" ")
    )


def _code(text: str) -> list[str]:
    """Every line of code in the skill: fenced blocks and inline `code` spans."""
    blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
    without_blocks = re.sub(r"```.*?```", "", text, flags=re.S)
    return [line for block in blocks for line in block.splitlines()] + re.findall(
        r"`([^`\n]+)`", without_blocks
    )


def _invocations() -> list[list[str]]:
    """Each ``idea-app ...`` command shown in the skill, as tokens after the program name.

    Only lines that start with the program count (after any ``VAR=value`` prefix), so a mention
    inside a quoted git commit message is not mistaken for a command. Shell comments are removed.
    """
    found = []
    for line in _code(_skill_text()):
        line = re.sub(r"^(?:\w+=\S+\s+)+", "", line.split(" #", 1)[0].strip())
        match = re.fullmatch(rf"{PROGRAM}(?:\s+(.*))?", line)
        if match and match.group(1):
            found.append(match.group(1).split())
    return found


def _options(command: click.Command) -> set[str]:
    return {opt for param in command.params for opt in [*param.opts, *param.secondary_opts]} | {
        "--help"
    }


def _ownership_row(project_type: str) -> tuple[str, str]:
    """The (managed, yours) cells of the file-ownership table row that covers ``project_type``."""
    for line in _skill_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and project_type in re.findall(r"`([a-z]+)`", cells[0]):
            return cells[1], cells[2]
    raise AssertionError(f"the file-ownership table has no row for {project_type}")


def test_the_skill_exists_and_has_valid_frontmatter():
    fields = _frontmatter(_skill_text())

    assert fields["name"] == SKILL_DIR.name == "idea-app-usage"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"])
    assert 0 < len(fields["description"]) <= 1024


def test_the_description_says_when_to_use_the_skill():
    assert "Use when" in _frontmatter(_skill_text())["description"]


def test_the_skill_shows_a_realistic_number_of_commands():
    assert len(_invocations()) >= 15


@pytest.mark.parametrize("tokens", _invocations(), ids=lambda t: " ".join(t)[:50])
def test_every_command_and_flag_shown_in_the_skill_exists(tokens):
    group_options = _options(cli)
    index = 0
    while index < len(tokens) and tokens[index].startswith("-"):
        assert tokens[index] in group_options, f"unknown global option {tokens[index]}"
        index += 1
    if index == len(tokens):
        return

    name = tokens[index]
    assert name in cli.commands, (
        f"'{PROGRAM} {name}' is not a command; the commands are {sorted(cli.commands)}"
    )
    allowed = _options(cli.commands[name])
    flags = [t.split("=", 1)[0] for t in tokens[index + 1 :] if t.startswith("--")]
    unknown = [flag for flag in flags if flag not in allowed]
    assert not unknown, f"'{PROGRAM} {name}' has no option(s) {unknown}; it has {sorted(allowed)}"


def test_every_command_is_covered_by_the_skill():
    mentioned = {tokens[0] for tokens in _invocations() if tokens and not tokens[0].startswith("-")}

    assert set(cli.commands) <= mentioned, (
        f"commands the skill never shows: {sorted(set(cli.commands) - mentioned)}"
    )


def _types_table_first_column() -> set[str]:
    """Every project type named in the first column of the 'Project types' table."""
    section = _skill_text().split("## Project types", 1)[1].split("\n## ", 1)[0]
    names = set()
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].startswith("`"):
            names.update(re.findall(r"`([a-z]+)`", cells[0]))
    return names


@pytest.mark.parametrize("project_type", PROJECT_TYPES)
def test_every_project_type_init_accepts_is_in_the_project_types_table(project_type):
    assert project_type in _types_table_first_column()


def test_the_project_types_table_names_no_type_that_init_rejects():
    assert _types_table_first_column() <= set(PROJECT_TYPES)


def test_init_arguments_the_skill_shows_use_real_project_types():
    shown = {
        tokens[1]
        for tokens in _invocations()
        if tokens[0] == "init"
        and len(tokens) > 1
        and not tokens[1].startswith("<")  # skip the <type> placeholder
    }

    assert shown <= set(PROJECT_TYPES)


def test_the_directory_prefixes_match_the_tool():
    text = _skill_text()

    assert f"{REPO_PREFIX}-{{name}}" in text
    assert f"{PKG_REPO_PREFIX}-{{name}}" in text


@pytest.mark.parametrize("project_type", PROJECT_TYPES)
def test_the_file_ownership_table_matches_the_files_the_tool_manages(project_type):
    managed_cell, _ = _ownership_row(project_type)
    documented = set(re.findall(r"`([^`]+)`", managed_cell))
    actual = set(get_tracked_files(project_type).values())

    assert documented == actual, (
        f"{project_type}: in the skill but not managed: {sorted(documented - actual)}; "
        f"managed but missing from the skill: {sorted(actual - documented)}"
    )


def test_the_skill_does_not_tell_agents_to_run_git_init_after_init():
    # `idea-app init` makes the first commit itself.
    assert "git init" in _skill_text()  # it is mentioned, to say not to
    for tokens in _invocations():
        assert tokens[:1] != ["git", "init"]
