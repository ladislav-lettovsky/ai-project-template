# Stdin mode for `scan_injection.py`

## Metadata

- spec_id: SPEC-20260515-scan-injection-stdin-mode
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T1
- repo: ai-project-template
- branch: spec/scan-injection-stdin-mode

## Context

`scripts/scan_injection.py` is the prompt-injection gate that runs as part of
`just check` and standalone via `just scan-injection`. Today it scans only
files on disk: callers pass paths (or rely on the default scan-target list),
and the script reads each file from the working tree before applying the
pattern catalogue.

In-flight artifacts — an MCP tool response that has just arrived, a payload
returned by a web fetch the agent is about to consume, a buffer captured
mid-pipeline — cannot be scanned without first writing them to disk. That is
clumsy in agent pipelines and creates short-lived files under `docs/external/`
or `.scratch/` purely to satisfy the scanner. A `--stdin` flag lets callers
pipe the buffer directly: agents and shell wrappers can scan responses inline
without persisting them, and the existing file-based interface stays exactly
as it is today.

This is a small, additive CLI extension. No new patterns, no new file types,
no change to the default scan set, and no change to the public Python API of
`scan_file` / `iter_targets`.

## Assumptions

- A1: The existing `INJECTION_PATTERNS` tuple is the authoritative set of
  strings worth detecting at this layer. This spec does not extend, reorder,
  or rephrase that list.
- A2: The whitespace-normalization behaviour added by
  `scan-injection-multiline` (collapse runs of whitespace before substring
  match) applies to stdin payloads too — stdin is just another byte buffer,
  and the same matcher should run on it.
- A3: Callers piping into `--stdin` are responsible for the encoding of what
  they pipe. The scanner reads stdin as UTF-8 with `errors="ignore"`, matching
  the file-mode behaviour in `scan_file`.
- A4: Standalone `--stdin` usage is the only stdin shape worth supporting in
  this spec. Mixing `--stdin` with positional path arguments in one
  invocation is rejected — it ambiguates what `<path>` means in the error
  message and complicates exit-code semantics for no observed use case.
- A5: A single stdin payload is bounded enough to read into memory in one
  buffer. The scanner already loads each scanned file entirely via
  `read_text`; stdin payloads are typically smaller than the on-disk artifacts
  it already handles.

## Decisions

- D1: Add a `--stdin` flag parsed by hand inside `main`, not by introducing
  `argparse`. The existing `main` is a positional-args-only function and the
  module is intentionally stdlib-minimal; a single boolean flag does not
  justify pulling in `argparse` and rewriting the call shape. Detection is a
  literal `"--stdin" in args` check before the path-iteration branch.
- D2: When `--stdin` is present, `main` reads `sys.stdin.read()` into a single
  buffer, runs the same matcher used by `scan_file` against that buffer, and
  emits hits using the sentinel path string `<stdin>`. Output line format is
  `ERROR: <stdin>: <pattern>` — identical to the file-mode format with
  `<stdin>` substituted for the filesystem path. This keeps any CI / log
  consumer that greps for `^ERROR:` working unchanged.
- D3: The matcher used by `--stdin` must be the same one used by file mode.
  Refactor `scan_file` to delegate to a new private helper
  `_scan_text(text: str) -> list[str]` that performs the lower-case +
  whitespace-collapse + pattern loop, and call that helper from both code
  paths. Single source of truth, no duplicated regex.
- D4: Exit codes for `--stdin` follow the existing contract: `0` if no
  pattern matches, `1` if at least one matches. Identical to file mode.
- D5: `--stdin` with positional path arguments is rejected at the top of
  `main` with exit code `2` and a stderr message
  `usage: scan_injection.py --stdin (no path arguments allowed)`. Exit code
  `2` is the conventional shell idiom for "usage error", distinct from `1`
  ("scan found a hit"). This matters: a wrapper script that greps for exit
  status `1` to mean "injection found" must not be tricked by a misuse error.
- D6: Stdin read uses `sys.stdin.read()` with the default encoding (UTF-8 on
  Python 3.12+ POSIX), and the buffer is treated as text. No binary mode.
  Encoding errors are not silently ignored at the stream layer (Python's
  default), but the helper lower-cases and processes whatever decoded text is
  produced.
- D7: An empty stdin payload (zero bytes) is treated as a clean scan: no
  output, exit `0`. The matcher returns `[]` for an empty buffer trivially.

## Problem Statement

There is no way to ask `scripts/scan_injection.py` to scan a buffer that has
not been written to disk. Concretely:

- An agent that has just received an MCP tool response and wants to gate the
  next step on a clean injection scan must first `write_text` the response to
  a temp file, invoke the scanner with that path, then delete the file. The
  temp-file dance is bookkeeping with no security value.
- A shell wrapper that wants to validate a `curl`-fetched HTML body before
  passing it into a downstream prompt has the same problem: it must redirect
  to a file under a scannable extension before invoking the scanner.

Adding `--stdin` removes the temp-file step. The pattern set, exit codes, and
output format remain identical, so existing automation is unaffected.

## Requirements (STRICT)

- [ ] R1: Invoking `scripts/scan_injection.py --stdin` with a payload piped on
  stdin that contains no `INJECTION_PATTERNS` entry exits `0` and produces no
  stdout output.
- [ ] R2: Invoking `scripts/scan_injection.py --stdin` with a payload piped on
  stdin that contains at least one `INJECTION_PATTERNS` entry exits `1` and
  prints one `ERROR: <stdin>: <pattern>` line to stdout per matched pattern,
  using the sentinel path string `<stdin>` and the original pattern string
  from `INJECTION_PATTERNS`.
- [ ] R3: Invoking `scripts/scan_injection.py --stdin` together with one or
  more positional path arguments exits with code `2` and emits a usage error
  to stderr. The scanner does NOT scan stdin or any path in this misuse case.
- [ ] R4: Existing file-mode behaviour is preserved byte-for-byte:
  - the default scan set (no arguments) still scans
    `DEFAULT_SCAN_TARGETS`,
  - explicit positional path arguments still scan those paths,
  - the output line format for file mode remains `ERROR: <path>: <pattern>`,
  - exit codes `0` (clean) and `1` (hit) remain the file-mode contract.
- [ ] R5: The `INJECTION_PATTERNS` tuple is unchanged by this spec — its
  membership, ordering, and string contents are byte-identical to the value
  present before this work begins.
- [ ] R6: The whitespace-normalization behaviour from
  `scan-injection-multiline` (collapse runs of whitespace before substring
  match) applies to stdin payloads as well as file payloads — a stdin buffer
  with a pattern split across newlines is detected.

## Non-Goals

- [ ] NG1: No new patterns added to `INJECTION_PATTERNS`. Pattern catalogue
  changes are a separate spec.
- [ ] NG2: No changes to red-zone files. `scripts/hooks/**`, `AGENTS.md`,
  `.claude/settings.json`, `justfile`, `pyproject.toml`, `uv.lock`, and
  `.pre-commit-config.yaml` are untouched.
- [ ] NG3: No support for reading multiple stdin payloads separated by a
  delimiter, no support for `--stdin -` shorthand, no support for `--stdin0`
  null-separated framing. One invocation, one buffer.
- [ ] NG4: No defence against base64-encoded, leet-speak, Unicode-lookalike,
  or comment-disguised payloads. False negatives against motivated attackers
  remain out of scope (per the existing module docstring).
- [ ] NG5: No new dependencies (runtime or dev). Stdlib only — no `argparse`
  introduction, no `click`, no `typer`.
- [ ] NG6: No changes to `scripts/lint_spec.py`, the `just check` recipe, the
  `just scan-injection` recipe, or the Stop hook. `--stdin` is invoked by
  agents and shell wrappers, not by `just`.
- [ ] NG7: No changes to the default scan-target list, the file-extension
  allowlist (`SCAN_EXTENSIONS`), or the directory-traversal logic in
  `iter_targets`.

## Interfaces

Files modified:

- `scripts/scan_injection.py`:
  - Add a private helper `_scan_text(text: str) -> list[str]` that performs
    lower-casing, whitespace-collapse normalization, and the
    `INJECTION_PATTERNS` substring loop. Returns the list of matched
    pattern strings.
  - Refactor `scan_file(path: Path) -> list[str]` to delegate to
    `_scan_text` after reading the file body. Signature unchanged.
  - Extend `main(argv: list[str] | None = None) -> int` to recognise
    `--stdin`. When the flag is present:
    - if any positional path argument is also present, write a usage error
      to stderr and return `2`;
    - otherwise read `sys.stdin.read()`, call `_scan_text` on the buffer,
      print one `ERROR: <stdin>: <pattern>` line per hit to stdout, and
      return `1` if any hit was produced, `0` otherwise.
  - `main`'s signature stays `(argv: list[str] | None = None) -> int`.

- `tests/test_scan_injection.py` — three new deterministic tests covering
  the clean-stdin, dirty-stdin, and existing file-mode regression cases
  (see Test Plan).

Files created: none.

Public Python API surface:

| Function | Signature | Change |
| --- | --- | --- |
| `scan_file` | `(path: Path) -> list[str]` | Body refactored to delegate to `_scan_text`. Behaviour identical. |
| `_scan_text` | `(text: str) -> list[str]` | New private helper. Not exported. |
| `iter_targets` | `(args: list[str]) -> list[Path]` | Unchanged. |
| `main` | `(argv: list[str] \| None = None) -> int` | Recognises `--stdin`. File-mode path unchanged. |

CLI behaviour:

| Invocation | Source | Output line format | Exit codes |
| --- | --- | --- | --- |
| `scan_injection.py` (no args) | default scan set on disk | `ERROR: <path>: <pattern>` | 0 clean / 1 hit |
| `scan_injection.py <path>...` | explicit paths on disk | `ERROR: <path>: <pattern>` | 0 clean / 1 hit |
| `scan_injection.py --stdin` | stdin buffer | `ERROR: <stdin>: <pattern>` | 0 clean / 1 hit |
| `scan_injection.py --stdin <path>` | misuse | usage error on stderr | 2 |

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs +
  scan-injection) remains green after this change.
- [ ] INV2: `scripts/scan_injection.py` remains stdlib-only; no new
  third-party imports and no `argparse` addition (per D1 / NG5).
- [ ] INV3: No red-zone file is modified by this work (per `AGENTS.md`
  "Red-zone files").
- [ ] INV4: The `ERROR: <path>: <pattern>` output line format for file mode
  is byte-identical to today's format. The new `--stdin` mode uses the same
  shape with the sentinel `<stdin>` substituted for `<path>`.
- [ ] INV5: Existing file-mode exit-code semantics preserved (0 = clean,
  1 = at least one hit). `--stdin` mode follows the same `0`/`1` contract;
  the new `2` exit code is reserved for `--stdin` misuse and is not reachable
  from file mode.
- [ ] INV6: `INJECTION_PATTERNS`, `SCAN_EXTENSIONS`, and
  `DEFAULT_SCAN_TARGETS` are unchanged in membership and order.
- [ ] INV7: The existing test suite for `scan_injection.py` continues to
  pass — adding `--stdin` must not regress any existing test.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes

> `scripts/scan_injection.py` is not in the red-zone enumeration in
> `AGENTS.md`, but it is invariant-protected via Invariant 3 ("Specs are
> documentation in `docs/specs/`, lint-enforced") and the `just check`
> pipeline depends on its exit-code contract. Extending the CLI with
> `--stdin` widens the invocation surface; the `yes` answer here drives
> `risk_tier: T1`. The Reviewer should confirm that file mode is unchanged
> and that the new exit code `2` is reachable only via the misuse path.

## Test Plan

All tests live in `tests/test_scan_injection.py`. Each test docstring cites
the requirement ID(s) it covers. All tests are deterministic and offline.
Tests that exercise `main` and need stdin use `monkeypatch.setattr(sys,
"stdin", io.StringIO(payload))` so they do not block on the real stdin.

- [ ] T1 -> covers R1, R4
  `test_stdin_clean_payload_exits_zero`: monkeypatch `sys.stdin` to a
  `StringIO` containing a clean payload (e.g. `"# Title\n\nclean body\n"`),
  call `scan_module.main(["--stdin"])`, assert return code is `0` and
  captured stdout is empty.

- [ ] T2 -> covers R2, R6
  `test_stdin_dirty_payload_exits_one_with_error_line`: monkeypatch
  `sys.stdin` to a `StringIO` containing the first entry of
  `INJECTION_PATTERNS` (for example, `INJECTION_PATTERNS[0]` on one line
  plus surrounding prose), call `scan_module.main(["--stdin"])`, assert
  return code is `1`, and assert captured stdout contains the exact line
  built from `INJECTION_PATTERNS[0]`. A second sub-assertion
  uses a newline-split payload built by joining the three words of
  `INJECTION_PATTERNS[0]` with `"\n"` to confirm R6 (whitespace
  normalization applies to stdin).

- [ ] T3 -> covers R3
  `test_stdin_with_path_argument_is_usage_error`: call
  `scan_module.main(["--stdin", str(tmp_path / "anything.md")])` and assert
  return code is `2`, captured stdout is empty, and captured stderr contains
  the substring `"--stdin"` and the substring `"path"`. No file is read.

- [ ] T4 -> covers R4, R5
  `test_file_mode_unchanged_regression`: write a clean file and a file
  containing the final entry of `INJECTION_PATTERNS` to `tmp_path`, call
  `scan_module.main([str(tmp_path)])`, assert return code is `1`, captured
  stdout contains a `bad.md` ERROR line for that pattern and does
  not contain any `ok.md` line, AND assert `scan_module.INJECTION_PATTERNS`
  equals the documented 12-tuple unchanged. This pins R4's file-mode
  contract and R5's pattern-catalogue invariant in one fast test.

> The existing tests
> (`test_main_scans_directory_and_reports_path`,
> `test_main_returns_zero_on_clean_dir`,
> `test_nonexistent_default_target_is_skipped`,
> `test_only_listed_extensions_are_scanned`,
> `test_injection_patterns_tuple_is_unchanged`,
> `test_injection_split_by_newlines_is_detected`,
> `test_injection_split_by_tabs_is_detected`,
> `test_injection_inline_single_space_still_detected`)
> already exercise file-mode and the whitespace-normalization path; T4 above
> deliberately adds a single end-to-end regression rather than duplicating
> them. T1–T3 are the new stdin-specific cases.

## Validation Contract

| Requirement | Validator |
| --- | --- |
| R1 | `uv run pytest tests/test_scan_injection.py::test_stdin_clean_payload_exits_zero` |
| R2 | `uv run pytest tests/test_scan_injection.py::test_stdin_dirty_payload_exits_one_with_error_line` |
| R3 | `uv run pytest tests/test_scan_injection.py::test_stdin_with_path_argument_is_usage_error` |
| R4 | `uv run pytest tests/test_scan_injection.py::test_file_mode_unchanged_regression` |
| R5 | `uv run pytest tests/test_scan_injection.py::test_file_mode_unchanged_regression` |
| R6 | `uv run pytest tests/test_scan_injection.py::test_stdin_dirty_payload_exits_one_with_error_line` |

## Edge Cases

- EC1: Empty stdin (`""`). Per D7, `_scan_text("")` returns `[]`, `main`
  returns `0`, stdout is empty. Implicitly covered by T1's clean-payload
  shape (a `StringIO("")` is a valid clean payload); no separate test
  needed.
- EC2: Stdin payload containing multiple distinct patterns. Each matched
  pattern produces its own `ERROR: <stdin>: <pattern>` line, ordered by
  the iteration order of `INJECTION_PATTERNS`. Same semantics as file mode.
- EC3: Stdin payload containing a pattern split across mixed whitespace
  (tabs, newlines, runs of spaces). Whitespace-collapse normalization
  (inherited from `scan-injection-multiline`) collapses them to a single
  space before substring match. Covered by the second sub-assertion of T2.
- EC4: `--stdin` appearing more than once on the command line
  (`--stdin --stdin`). Treated identically to a single `--stdin`. The
  detection in D1 is `"--stdin" in args`, so duplicates are a no-op. No
  separate test.
- EC5: Very large stdin payload. The buffer is read whole; no streaming.
  This matches the file-mode behaviour (`read_text` reads each file whole).
  No size limit is imposed by this spec.
- EC6: Stdin payload containing non-UTF-8 bytes. Python's text-mode stdin
  decodes using the platform default (UTF-8 on POSIX); decoding errors
  propagate as today. Out of scope for this spec.
- EC7: `--stdin` with `-` or `--` as positional arguments. Both are treated
  as positional paths and trigger the misuse error (R3 / D5). Conservative,
  matches the explicit usage message.

## Security / Prompt-Injection Review

- source: stdin. `--stdin` accepts a buffer that, in agent pipelines, will
  typically originate from an MCP tool response, a web fetch, or other
  external input the caller has chosen to validate. This is precisely the
  shape of input the scanner exists to inspect.
- risk: low
- mitigation: not required. The buffer is matched against a fixed pattern
  catalogue using passive substring comparison; the scanner does not execute,
  parse, or render the input. The whole point of this feature is to inspect
  potentially-malicious content without persisting it, and the scanner's
  matching logic does not itself become an injection vector. The result
  (`0`/`1`/`2` exit and `ERROR: <stdin>: ...` lines) is mechanical output the
  caller acts on; it is not fed back into a prompt.

## Observability

None required. The scanner already prints `ERROR: <path>: <pattern>` lines
to stdout for every match; `--stdin` mode uses the same channel with
`<stdin>` substituted for `<path>`. Usage errors (R3) go to stderr. No
metrics, telemetry, or new logging.

## Rollback / Recovery

Purely additive CLI extension. Revert the single commit that adds `--stdin`,
`_scan_text`, and the three new tests. The file-mode code path is preserved
end-to-end, so reverting restores the prior CLI without affecting any
caller that uses file paths (which is every caller today). No data, no
schema, no migration, no feature flag.

If a caller adopts `--stdin` and later wants it removed, the revert is a
single-commit operation. Callers can pivot back to the temp-file pattern.

## Implementation Slices

1. **Slice 1 — Refactor `scan_file` into `_scan_text` + `scan_file`.** In
   `scripts/scan_injection.py`, introduce private helper `_scan_text(text:
   str) -> list[str]` that performs the existing lower-case +
   whitespace-collapse + pattern-loop logic. Refactor `scan_file` to read
   the file body and delegate. No behaviour change. Run `just check`; all
   existing tests must pass unchanged.

2. **Slice 2 — Add `--stdin` to `main`.** In the same file, detect
   `"--stdin" in args` at the top of `main`. If present together with any
   non-flag positional argument, write the usage error to stderr and
   return `2`. Otherwise read `sys.stdin.read()`, call `_scan_text`, emit
   `ERROR: <stdin>: <pattern>` lines, and return `1` if any hit, `0`
   otherwise.

3. **Slice 3 — Tests.** Add T1, T2, T3, T4 to `tests/test_scan_injection.py`
   with docstrings citing requirement IDs. Use
   `monkeypatch.setattr(sys, "stdin", io.StringIO(...))` for stdin-driven
   tests so they do not block. Run `just check`; commit.

> Slices 1, 2, 3 ship in one PR. The split exists to document the order of
> logical concerns inside the diff; the PR does not need to land as three
> commits.

## Done When

- [ ] All requirement IDs (R1–R6) satisfied.
- [ ] Decisions D1–D7 preserved, or any deviation explicitly noted in the
  PR with rationale.
- [ ] Tests T1–T4 present in `tests/test_scan_injection.py`, with docstrings
  citing the requirement IDs they cover.
- [ ] Validation Contract satisfied — every R* maps to a passing pytest
  invocation.
- [ ] `just check` green locally (ruff + ty + pytest + lint-changed-specs +
  scan-injection).
- [ ] CI green.
- [ ] Invariants INV1–INV7 hold.
- [ ] Branch name starts with `spec/scan-injection-stdin-mode` (Invariant 1).
- [ ] PR description links this spec at
  `docs/specs/scan-injection-stdin-mode.md`.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
  block.
