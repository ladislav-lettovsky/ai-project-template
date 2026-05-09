"""Validate the Reviewer's structured-JSON output extracted from a PR body.

Usage:
    uv run scripts/validate_reviewer.py <pr-body-file>
    uv run scripts/validate_reviewer.py -          # read PR body from stdin

Exit codes:
    0 — extracted JSON validated successfully against ``.reviewer-schema.json``.
    1 — failed: markers missing, JSON malformed, or schema violation.
        Specific error printed to stderr.
    2 — usage error (no args, file not found, schema not found).

Design notes:
    * Extraction uses regex on the literal ``<!-- REVIEWER_JSON --> ...
      <!-- /REVIEWER_JSON -->`` markers. If multiple blocks are present
      it's an error — the Reviewer should produce exactly one. (This
      matches the fragility documented in blueprint §6 Open Q #5; we
      fail loudly rather than silently picking the first.)
    * The extracted content may itself be wrapped in a markdown
      code fence (```` ```json ... ``` ````). The extractor strips that
      fence if present. JSON without the inner fence is also accepted.
    * Schema validation uses the ``jsonschema`` library, Draft 2020-12.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / ".reviewer-schema.json"

# The PR-body fence markers. Match literally, case-sensitive, with
# optional whitespace inside the comment to tolerate hand-typed bodies.
FENCE_RE = re.compile(
    r"<!--\s*REVIEWER_JSON\s*-->(.*?)<!--\s*/REVIEWER_JSON\s*-->",
    re.DOTALL,
)

# Optional inner Markdown fence: ```json\n ... \n```
MD_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n(.*?)\n\s*```\s*$",
    re.DOTALL,
)


def extract_json_text(pr_body: str) -> str:
    """Return the JSON text between the REVIEWER_JSON markers.

    Raises ValueError if zero, or more than one, marker pair is found,
    or if the block is empty.
    """
    matches = FENCE_RE.findall(pr_body)
    if not matches:
        raise ValueError(
            "no <!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON --> block found in PR body"
        )
    if len(matches) > 1:
        raise ValueError(f"found {len(matches)} REVIEWER_JSON blocks; expected exactly one")
    inner = matches[0].strip()
    if not inner:
        raise ValueError("REVIEWER_JSON block is empty")
    md_match = MD_FENCE_RE.match(inner)
    if md_match:
        inner = md_match.group(1).strip()
    return inner


def validate(pr_body: str, schema: dict) -> list[str]:
    """Return a list of validation error messages. Empty list = valid."""
    try:
        json_text = extract_json_text(pr_body)
    except ValueError as e:
        return [str(e)]
    try:
        instance = json.loads(json_text)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"]
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [
        f"schema violation at {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in errors
    ]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(
            "usage: validate_reviewer.py <pr-body-file>\n"
            "       validate_reviewer.py -          # read from stdin",
            file=sys.stderr,
        )
        return 2

    pr_body_arg = args[0]
    if pr_body_arg == "-":
        pr_body = sys.stdin.read()
    else:
        path = Path(pr_body_arg)
        if not path.is_file():
            print(f"ERROR: {path}: file not found", file=sys.stderr)
            return 2
        pr_body = path.read_text(encoding="utf-8")

    if not SCHEMA_PATH.is_file():
        print(f"ERROR: schema not found at {SCHEMA_PATH}", file=sys.stderr)
        return 2
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    errors = validate(pr_body, schema)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
