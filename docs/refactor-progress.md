# Refactor progress

## Run

- Date: 2026-11-28 (Asia/Shanghai).
- Repository: `Ukannn/codex-novel-to-comic-studio`.
- Baseline: `c43fa59d2c717e6761ea960c6f5a052a99564b8a`.
- Integration branch: `refactor/architecture-governance-20261128`.
- Execution: isolated Git worktrees; independent rendering and validation owners;
  separate read-only architecture reviewer.
- Compatibility policy: [architecture](architecture.md) and [decisions](architecture-decisions.md).

## Completed checkpoints

### 0. Full-repository inventory and behavior baseline

- Read repository instructions, business workflow, complete Python module map,
  configuration, existing tests and two-commit history.
- Confirmed sibling novel workspaces have the same tracked tree; scope remains
  the reusable generic repository.
- `python3 -m unittest discover -s tests -v`: **11/11 passing**.
- `python3 TOOLS/check_state.py .`: `phase0_ingest`, as expected for a clean clone.
- Architecture, ownership, duplicate inventory, alternatives and deferred
  decisions recorded before implementation.

### 1. Canonical configuration and persistence

- `dcac414`: one JSON read/write boundary; source manifest, task files and later
  rendering/QC callers migrated to it. Failed serialization/replacement leaves
  existing files intact. Existing modes and symlink destinations are preserved;
  newly created artifacts use private temporary-file permissions.
- `c8bb9c2`: frozen production settings and explicit configuration precedence.
  Wrong root types, unhashable enum inputs, non-integer counts and contradictory
  resolution choices now produce preference errors instead of accidental coercion.
- Independent review found a descriptor leak if `fdopen` fails; `41b6879` fixed
  ownership transfer and added a reproducing regression. Reviewer verified fix.

### 2. Validation ownership and pure domain APIs

- `ffb1443` establishes file/CLI/report baselines before code changes.
- `0f03f66` moves director checks into the package and adds pure page-plan/script
  validators. Stable CLI re-exports retain real callers. Replaced readers,
  envelopes and duplicated page-count checks were removed.
- `6b4d1f7` rejects JSON booleans/floats/strings masquerading as integer counts or
  identifiers. Valid documents keep their existing reports and diagnostic order.
- Independent review passed. The extraction was also compared against 238
  malformed-structure mutations before the deliberate integer hardening.

### 3. Rendering, primary QC and binding

- `ce671a2` captures image pixels/geometry, missing-panel placeholders, export
  ordering and report contracts.
- `4968068` replaces both grid algorithms with `layout.panel_boxes`; composition
  keeps margin 0 / gutter 8 and lettering keeps margin 82 / gutter 34.
- `fd2bcb4` supports finished-page-only QC while retaining explicit fallback art
  checks. Corrupt images become blocking report issues and do not hide later pages.
- `cfdde7f` releases PDF image buffers on decode/write failures.
- `0a04655` and `4609b0b` finish canonical persistence/default migration across
  rendering and four command adapters. Existing size aliases remain available.
- Independent review passed for every batch, including the dependent integration.

### 4. Configured image tasks and state recovery

- `934ff53` records the exact standalone prompt and reference selection before
  `0d2db45` adds supplied production settings. No-preferences calls retain the
  old Chinese prompt; the project's explicit English choice now takes effect.
- `f5534b5` records freshness, chapter precedence and script-owned page lists.
- `a9eb633` reads and validates a script once per inspection; deletes three old
  page-number readers and the unused phase-table column. No persistent cache,
  new state names or changed approval semantics were introduced.
- Independent malformed-file probes and targeted review passed.

### 5. Enforceable architecture and Agent workflow

- `9b3e351` aligns Agent role instructions with configured language/canvas and
  documents worktree/file ownership for parallel engineering. A nonexistent
  background-document reference was removed; package exports were made complete.
- `34c3e97` adds AST direction/cycle/default/persistence rules, negative guard
  fixtures and all 11 public CLI help/import contracts. CI runs the same suite
  on Python 3.10, 3.12 and 3.13. Official action tag availability was verified.
- `e53cca0` extends the persistence rule to text, finishes the module/API map and
  synchronizes English, Chinese and Japanese setup/configuration guidance.
- The guard checks syntax and defined dependency policy, not arbitrary semantic
  correctness; independent review is still required.

### 6. Failure-safe initial ingest and workspace boundary

- Full-system independent review reproduced a pre-existing false completion:
  failing the first chapter write still left `novel.txt` visible to state.
- `13b822c` extracts the same atomic text publisher, migrates chapter/novel text,
  and publishes chapters, manifest and then `novel.txt`. Before the fix, the new
  regression suite had 5 failures / 1 pass; afterward all 6 passed.
- `1f5e6f8` keeps generated story bibles and root comic plans out of Git by
  default. Tools, templates and original demo assets remain trackable.
- Independent review confirmed both batches; existing re-ingest remains explicitly
  nontransactional and no historical artifacts are deleted.

## Verification and handoff

- Original suite: **11/11 passing**; integrated suite: **96/96 passing**.
- Independent full gate at `1f5e6f8`: unittest, compileall and `git diff --check`
  passed. The subsequent text-boundary extension passed all 8 architecture tests.
- Independent end-to-end smoke: **19 successful subprocess invocations across
  all 11 commands**, using a temporary synthetic source and images. Covered
  parsing, plan/script/director validation, configured English tasks, composition,
  normalization, fallback lettering, both QC modes, two-page PDF/CBZ and state
  progression to `complete`. Temporary production data was removed.
- Local verification uses Python 3.12 and Pillow 13. Remote matrix results are
  reported by GitHub checks; configuration alone is not evidence of a remote run.
- No actual image-generation service or user novel was used. Live image quality,
  human editorial review and cross-platform CJK font quality are outside these
  automated checks.
- Safe governance queue is closed. Remaining decisions and scoped enhancements
  are in [the task pool](refactor-backlog.md). Preserve this branch for review;
  the default branch and sibling repositories are not migration targets here.
