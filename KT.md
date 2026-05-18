# KT — sync-agent

> Last updated: 2026-05-18T16:30 | Trigger: manual | Staleness: Fresh

---

## 1. Project Overview

`sync-agent` is a Python CLI tool that does two things: (1) merges segmented `.odt` diary/journal files between two locations using cosine-similarity deduplication, and (2) mirrors file trees by copying newer files from a source tree to a target tree. It was converted and heavily refactored from a Jupyter notebook (`oldcode/`). Current status: **Stabilizing** — all code and tests are complete; one session-end bookkeeping task (MANIFEST regeneration) is pending.

---

## 2. Goals & Constraints

**Goals:**
- Correct, complete CLI replacement for the original notebook workflows
- Source-authoritative ODT merge with similarity-based deduplication and legacy archiving
- Mirror sync with shallow-list, keep-list, exclude-list, cutoff, and future-timestamp guard
- 54-test suite covering all public behaviour; all tests must pass before delivery
- Manifest-verified file integrity per `ken-manifest-verify` skill

**Constraints:**
- Python 3.10+ (uses `X | Y` union type hints)
- Windows-primary; `pywin32` auto-installed on Windows
- `src/` layout: package lives under `src/sync_agent/`, not at project root
- `loguru` for all logging; no `print()` in library code
- CRLF-normalised SHA-256 hashes in MANIFEST.txt

**Non-goals:**
- Two-way sync (source always wins on similarity conflicts)
- ODT format other than the flat `<M/D/YYYY>` paragraph tag convention
- Deletion propagation in mirror mode (mirror is additive only)

---

## 3. Prototypes & Examples

Original notebook code preserved in `oldcode/` for reference:
- `oldcode/proc_docs.py` — ODT parse/merge logic
- `oldcode/similarity.py` — original similarity implementation
- `oldcode/copyindate_ed.py` — mirror/copy workflow
- `oldcode/nlgutls.py` — utility helpers

Quick usage examples are in `docs/README.md`. Four concrete workflows are in `docs/API.md`.

---

## 4. Architecture & Key Files

```
sync_agent_source/
├── src/
│   └── sync_agent/
│       ├── __init__.py          # version string only
│       ├── similarity.py        # cosine similarity over token sets (module-level fn)
│       ├── content_engine.py    # SegmentedODFHandler (parse/save) + normalize()
│       ├── sync_managers.py     # ContentAwareSync + SimpleMirrorSync
│       └── cli.py               # argparse CLI; content and mirror subcommands
├── tests/
│   └── test_sync.py             # 54 tests; covers all public API
├── docs/
│   ├── README.md                # ≤500-word entry point with quick start
│   ├── CHEATSHEET.md            # copy-paste reference + parameter tables
│   └── API.md                   # full signatures + 4 workflows
├── oldcode/                     # original notebook code (reference only, not tracked)
├── pyproject.toml               # src layout; [tool.setuptools.packages.find] where=["src"]
├── verify_install.py            # reads MANIFEST.txt, verifies per-file + bundle hash
├── MANIFEST.txt                 # ⚠️ STALE — still has old sync_agent/ paths (see §7)
└── KT.md                        # this file
```

**Key design decisions:**
- `similarity()` is a plain module-level function (not a class) — a single-method stateless class is navigation hell per `ken-code-quality`
- `from dateutil.parser import parse as parse_date` — avoids shadowing by the `parse()` method on `SegmentedODFHandler`
- `sync_files()` counts `added` relative to `tgt_data` (not `src_data`) so a missing target correctly counts as gaining all source segments
- Legacy archiving: before overwriting any target in directory mode, the current target is moved to `tgt/legacy/<stem>_YYYY_MM_DD.odt`

---

## 5. Recent Decisions & Rationale

- **2026-05-18** — Moved to `src/` layout (`src/sync_agent/`). Reason: Ken's standard project structure has `src/`, `tests/`, `docs/` as siblings. `pyproject.toml` updated with `[tool.setuptools.packages.find] where = ["src"]`. Tests confirmed passing (54/54) after `pip install -e .` with new layout.

- **2026-05-18** — Refactored `SimilarityEngine` class to a module-level `similarity()` function. Reason: single-method stateless class is anti-pattern per `ken-code-quality` skill.

- **2026-05-18** — Renamed `from dateutil.parser import parse` → `parse as parse_date`. Reason: `parse` collided with the `SegmentedODFHandler.parse()` method name, confusing readers.

- **2026-05-18** — Removed `.encode().decode()` idiom from `content_engine.py`. Reason: Python 2 no-op; no effect in Python 3.

- **2026-05-18** — Fixed `sync_files()` added-count baseline from `src_data` to `tgt_data`. Reason: with src as baseline, a missing target always returned 0 and was never written.

- **2026-05-18** — Written full `docs/` suite: README.md, CHEATSHEET.md, API.md (with 4 workflows) per `code-documentation-writing` skill.

- **2026-05-18** — Fixed `SimpleMirrorSync._should_copy` future-timestamp guard. `self._now` was captured in `__init__`; tests that created files and then called `sync_tree` (or `_should_copy` directly) had files with mtimes slightly after `_now` due to Windows sub-millisecond clock jitter between the filesystem and `datetime.now()`. Fix: (1) `sync_tree` refreshes `self._now` at entry so files pre-dating the run are never blocked; (2) guard threshold changed to `_now + timedelta(seconds=1)` to absorb filesystem/clock-source jitter while still catching real external-drive skew (minutes/hours). All 54 tests now pass on Windows.

---

## 6. Open Questions & Blockers

1. **MANIFEST.txt has stale paths** — still references `sync_agent/` not `src/sync_agent/`. Needs regeneration in next session. Owner: Claude. Added: 2026-05-18.

2. **ken-code-quality skill needs project layout section** — agreed to add a "Project layout" section documenting `src/tests/docs` as the strong default. Not yet done. Owner: Claude. Added: 2026-05-18.

---

## 7. Next Steps

1. **Start a new session** connected only to `sync_agent_source/` (the renamed folder).
2. **Regenerate MANIFEST.txt** — update all 5 source paths from `sync_agent/` to `src/sync_agent/`, recompute per-file hashes and bundle hash, run `verify_install.py` to confirm all OK.
3. **Amend `ken-code-quality` skill** — add "Project layout" section with the `src/tests/docs` standard structure and `pyproject.toml` `packages.find` requirement.
4. **Run `pytest tests/ -q`** — confirm 54/54 still pass in the clean session.
5. **Present** `MANIFEST.txt` and the updated skill to Ken.

---

## 8. Last Updated

2026-05-18T16:00 | Trigger: manual | Staleness: Fresh — Initial KT creation. Captures post-refactor, post-src-layout state. MANIFEST regeneration and skill amendment are the only outstanding items.
