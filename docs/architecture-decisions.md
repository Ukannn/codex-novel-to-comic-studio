# Architecture decisions

## ADR-001 — Keep the local toolkit architecture (accepted)

The product is a recoverable, file-based editorial pipeline. Options considered:
(1) convert it into an installed application/framework; (2) move all files into a
new layered hierarchy; (3) strengthen existing module boundaries in place.
Choose (3): it removes proven duplication without adding deployment complexity
or breaking documented `python3 TOOLS/...` commands. No backend, registry,
dependency-injection container or new database is justified.

## ADR-002 — Share mechanics, preserve domain meaning (accepted)

Options: retain duplicated validators/layout code; introduce a universal schema
and rendering framework; or extract only demonstrated common mechanisms.
Choose the last option. Plan and script remain separate domain validators.
Composition and lettering share grid geometry but retain different margins and
gutters. Their fallback purpose is a real contract, not a redundant product.

Deletion test: removing a CLI adapter breaks documented commands; removing a
shared geometry function would reintroduce two copies of the algorithm. A
one-line forwarding module with no contract or policy is not added.

## ADR-003 — Explicit production preferences, stable standalone defaults (accepted)

Options: load project JSON at import time; discover configuration by walking
parent directories; or accept an explicit preferences path and resolve it once
at the command boundary. Choose explicit `--preferences` with precedence
`explicit CLI flag > supplied preferences > legacy standalone default`.
There is no hidden filesystem search or import-time configuration state.

`config.py` owns runtime defaults, legal values and a frozen production settings
value. `config/user-preferences.json` owns the selected project's choices; it is
not a second implementation of validation rules. The project currently selects
English, while standalone image tasks historically requested Chinese. Explicit
configuration fixes that mismatch without silently changing old invocations.

## ADR-004 — Atomic JSON files, not a transaction framework (accepted)

Options: keep ad hoc writes; add a database/journal; or centralize UTF-8 JSON reads
and atomic same-directory file replacement. Choose the last. Serialization
completes before a destination is replaced; failed writes preserve the old file
and remove the temporary file. File/JSON failures remain ordinary exceptions so
domain validators can translate them into their established report format.

This protects readers from truncated individual JSON files. It does not promise
locking, last-writer conflict resolution, multi-file atomicity or stale approval
detection. Shared files still have one owner during parallel work.

## ADR-005 — Preserve current approval semantics (accepted; enhancements deferred)

State currently validates the plan/script but checks only existence/freshness of
later artifacts. Existing tests intentionally use placeholder briefs and `{}` QC.
Turning those checks into strict production approval gates would change recovery
and completion behavior. Keep phase names and precedence while simplifying reads.
Track strict QC, content approval and artifact hashes separately for a product
decision. The current engineering task does not invoke image production gates.
